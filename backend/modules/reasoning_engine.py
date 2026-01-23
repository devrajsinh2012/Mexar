"""
MEXAR Core Engine - Hybrid Reasoning Engine (RAG Version)
Pure RAG with Source Attribution + Faithfulness scoring.
No CAG preloading - dynamic retrieval per query.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import networkx as nx
from difflib import SequenceMatcher
import numpy as np

from utils.groq_client import get_groq_client, GroqClient
from utils.hybrid_search import HybridSearcher
from utils.reranker import Reranker
from utils.source_attribution import SourceAttributor
from utils.faithfulness import FaithfulnessScorer
from fastembed import TextEmbedding
from core.database import SessionLocal
from models.agent import Agent
from models.chunk import DocumentChunk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    Pure RAG reasoning engine with:
    1. Hybrid search (semantic + keyword)
    2. Cross-encoder reranking
    3. Source attribution (inline citations)
    4. Faithfulness scoring
    """
    
    # Domain guardrail threshold (lowered for better general question handling)
    DOMAIN_SIMILARITY_THRESHOLD = 0.05
    
    def __init__(
        self,
        groq_client: Optional[GroqClient] = None,
        data_dir: str = "data/agents"
    ):
        """
        Initialize the reasoning engine.
        
        Args:
            groq_client: Optional pre-configured Groq client
            data_dir: Legacy parameter, kept for compatibility
        """
        self.client = groq_client or get_groq_client()
        self.data_dir = Path(data_dir)
        
        # Initialize embedding model (384 dim - matches compiler)
        try:
            self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("FastEmbed bge-small-en-v1.5 loaded (384 dim)")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
        
        # Initialize RAG components
        self.searcher = HybridSearcher(self.embedding_model) if self.embedding_model else None
        self.reranker = Reranker()
        self.attributor = SourceAttributor(self.embedding_model)
        self.faithfulness_scorer = FaithfulnessScorer()
        
        # Cache for loaded agents
        self._agent_cache: Dict[str, Dict] = {}
    
    def reason(
        self,
        agent_name: str,
        query: str,
        multimodal_context: str = ""
    ) -> Dict[str, Any]:
        """
        Main reasoning function - Pure RAG with Attribution.
        
        Args:
            agent_name: Name of the agent to use
            query: User's question
            multimodal_context: Additional context from audio/image/video
            
        Returns:
            Dict containing:
                - answer: Generated answer with citations
                - confidence: Confidence score (0-1)
                - in_domain: Whether query is in domain
                - explainability: Full explainability data
        """
        # Load agent from Supabase
        agent = self._load_agent(agent_name)
        
        # Combine query with multimodal context
        full_query = query
        if multimodal_context:
            full_query = f"{query}\n\n[ADDITIONAL CONTEXT]\n{multimodal_context}"
        
        # Step 1: Check domain guardrail
        in_domain, domain_score = self._check_guardrail(
            full_query,
            agent["domain_signature"],
            agent["prompt_analysis"]
        )
        
        if not in_domain:
            return self._create_out_of_domain_response(
                query=query,
                domain=agent["prompt_analysis"].get("domain", "unknown"),
                domain_score=domain_score
            )
        
        # Step 2: Hybrid Search (semantic + keyword)
        search_results = []
        if self.searcher:
            search_results = self.searcher.search(full_query, agent["id"], top_k=20)
        
        if not search_results:
            # Fallback to simple query
            return self._create_no_results_response(query, agent)
        
        # Step 3: Rerank with cross-encoder
        chunks = [r[0] for r in search_results]
        rrf_scores = [r[1] for r in search_results]
        
        reranked = self.reranker.rerank(full_query, chunks, top_k=5)
        top_chunks = [r[0] for r in reranked]
        rerank_scores = [r[1] for r in reranked]
        
        # Step 4: Generate answer with focused context
        context = "\n\n---\n\n".join([c.content for c in top_chunks])
        answer = self._generate_answer(
            query=query,  # Use original query, not full_query
            context=context,
            system_prompt=agent["system_prompt"],
            multimodal_context=multimodal_context  # Pass multimodal context separately
        )
        
        # Step 5: Source Attribution
        chunk_embeddings = None
        if self.embedding_model:
            try:
                chunk_embeddings = list(self.embedding_model.embed([c.content for c in top_chunks]))
            except:
                pass
        
        attribution = self.attributor.attribute(answer, top_chunks, chunk_embeddings)
        
        # Step 6: Faithfulness Scoring
        faithfulness_result = self.faithfulness_scorer.score(answer, context)
        
        # Step 7: Calculate Confidence
        top_similarity = rrf_scores[0] if rrf_scores else 0
        top_rerank = rerank_scores[0] if rerank_scores else 0
        
        confidence = self._calculate_confidence(
            top_similarity=top_similarity,
            rerank_score=top_rerank,
            faithfulness=faithfulness_result.score
        )
        
        # Step 8: Build Explainability
        explainability = self._build_explainability(
            query=query,
            multimodal_context=multimodal_context,
            chunks=top_chunks,
            rrf_scores=rrf_scores[:5],
            rerank_scores=rerank_scores,
            attribution=attribution,
            faithfulness=faithfulness_result,
            confidence=confidence,
            domain_score=domain_score
        )
        
        logger.info(f"Reasoning complete: confidence={confidence:.2f}, chunks={len(top_chunks)}, faithfulness={faithfulness_result.score:.2f}")
        
        return {
            "answer": attribution.answer_with_citations,
            "confidence": confidence,
            "in_domain": True,
            "reasoning_paths": [],  # Legacy, kept for compatibility
            "entities_found": [],  # Legacy, kept for compatibility
            "explainability": explainability
        }
    
    def _load_agent(self, agent_name: str) -> Dict[str, Any]:
        """Load agent from Supabase (with caching)."""
        if agent_name in self._agent_cache:
            return self._agent_cache[agent_name]
        
        db = SessionLocal()
        try:
            agent = db.query(Agent).filter(Agent.name == agent_name).first()
            
            if not agent:
                raise ValueError(f"Agent '{agent_name}' not found")
            
            agent_data = {
                "id": agent.id,
                "name": agent.name,
                "system_prompt": agent.system_prompt,
                "domain": agent.domain,
                "domain_signature": agent.domain_signature or [],
                "prompt_analysis": agent.prompt_analysis or {},
                "knowledge_graph": agent.knowledge_graph_json or {},
                "chunk_count": agent.chunk_count or 0
            }
            
            self._agent_cache[agent_name] = agent_data
            return agent_data
        finally:
            db.close()
    
    def _check_guardrail(
        self,
        query: str,
        domain_signature: List[str],
        prompt_analysis: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """Check if query matches the domain."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        matches = 0
        bonus_matches = 0
        
        # Check domain match
        domain = prompt_analysis.get("domain", "")
        if domain.lower() in query_lower:
            bonus_matches += 3
        
        # Check sub-domains
        for sub_domain in prompt_analysis.get("sub_domains", []):
            if sub_domain.lower() in query_lower:
                bonus_matches += 2
        
        # Check domain keywords
        for keyword in prompt_analysis.get("domain_keywords", []):
            if keyword.lower() in query_lower:
                bonus_matches += 1.5
        
        # Check signature keywords with fuzzy matching
        signature_lower = [kw.lower() for kw in (domain_signature or [])]
        
        for word in query_words:
            if len(word) < 3:
                continue
            for kw in signature_lower[:100]:
                if self._fuzzy_match(word, kw) > 0.75:
                    matches += 1
                    break
                if word in kw or kw in word:
                    matches += 0.5
                    break
        
        # Calculate score
        max_possible = max(1, min(len(query_words), 10))
        base_score = matches / max_possible
        bonus_score = min(0.5, bonus_matches * 0.1)
        score = min(1.0, base_score + bonus_score)
        
        if bonus_matches >= 1:
            score = max(score, 0.2)
        
        is_in_domain = score >= self.DOMAIN_SIMILARITY_THRESHOLD
        
        logger.info(f"Guardrail: score={score:.2f}, matches={matches}, bonus={bonus_matches}, in_domain={is_in_domain}")
        
        return is_in_domain, score
    
    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Calculate fuzzy match ratio."""
        return SequenceMatcher(None, s1, s2).ratio()
    
    def _generate_answer(
        self,
        query: str,
        context: str,
        system_prompt: str,
        multimodal_context: str = ""
    ) -> str:
        """Generate answer using LLM with retrieved context and multimodal data."""
        
        # Build multimodal section if present
        multimodal_section = ""
        if multimodal_context:
            multimodal_section = f"""\n\nMULTIMODAL INPUT (User uploaded media):
{multimodal_context}

IMPORTANT: When the user asks about images, audio, or other uploaded media, 
use the descriptions above to answer their questions. The multimodal input 
contains AI-generated descriptions of what the user has uploaded."""
        
        full_system_prompt = f"""{system_prompt}

RETRIEVED KNOWLEDGE BASE CONTEXT:
{context[:80000]}
{multimodal_section}

IMPORTANT INSTRUCTIONS:
1. Answer using the retrieved context AND any multimodal input provided
2. If the user asks about uploaded images/audio, use the MULTIMODAL INPUT section
3. If asking about knowledge base topics, use the RETRIEVED CONTEXT
4. If information is not available in any source, say "I don't have information about that"
5. Be specific and cite sources when possible
6. Be concise but comprehensive
7. If you quote directly, use quotation marks
"""
        
        try:
            answer = self.client.analyze_with_system_prompt(
                system_prompt=full_system_prompt,
                user_message=query,
                model="chat"
            )
            return answer
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "I apologize, but I encountered an error processing your query. Please try again."
    
    def _calculate_confidence(
        self,
        top_similarity: float,
        rerank_score: float,
        faithfulness: float
    ) -> float:
        """
        Calculate confidence score based on RAG metrics.
        
        Calibrated to provide meaningful scores:
        - High retrieval + high faithfulness = high confidence
        - Low retrieval = capped confidence
        """
        # Normalize rerank score (cross-encoder outputs vary)
        # Typical range is -10 to +10, normalize to 0-1
        norm_rerank = min(1.0, max(0, (rerank_score + 10) / 20))
        
        # Normalize RRF score (typically 0 to 0.03)
        norm_similarity = min(1.0, top_similarity * 30)
        
        # Weighted combination
        confidence = (
            norm_similarity * 0.35 +      # Retrieval quality
            norm_rerank * 0.30 +           # Rerank confidence
            faithfulness * 0.25 +          # Grounding quality
            0.10                           # Base floor for in-domain
        )
        
        # Apply thresholds
        if norm_similarity > 0.7 and faithfulness > 0.8:
            confidence = max(confidence, 0.75)
        elif norm_similarity < 0.3:
            confidence = min(confidence, 0.45)
        
        return round(min(0.95, max(0.15, confidence)), 2)
    
    def _build_explainability(
        self,
        query: str,
        multimodal_context: str,
        chunks: List,
        rrf_scores: List[float],
        rerank_scores: List[float],
        attribution,
        faithfulness,
        confidence: float,
        domain_score: float
    ) -> Dict[str, Any]:
        """Build comprehensive explainability output."""
        return {
            "why_this_answer": {
                "summary": f"Answer derived from {len(chunks)} retrieved sources with {faithfulness.score*100:.0f}% faithfulness",
                "sources": [
                    {
                        "citation": src["citation"],
                        "source_file": src["source"],
                        "content_preview": src["preview"][:150] if src.get("preview") else "",
                        "relevance_score": f"{src.get('similarity', 0)*100:.0f}%"
                    }
                    for src in attribution.sources
                ]
            },
            "confidence_breakdown": {
                "overall": f"{confidence*100:.0f}%",
                "domain_relevance": f"{domain_score*100:.0f}%",
                "retrieval_quality": f"{rrf_scores[0]*100:.1f}%" if rrf_scores else "N/A",
                "rerank_score": f"{rerank_scores[0]:.2f}" if rerank_scores else "N/A",
                "faithfulness": f"{faithfulness.score*100:.0f}%",
                "claims_supported": f"{faithfulness.supported_claims}/{faithfulness.total_claims}"
            },
            "unsupported_claims": faithfulness.unsupported_claims[:3],
            "inputs": {
                "original_query": query,
                "has_multimodal": bool(multimodal_context),
                "chunks_retrieved": len(chunks)
            },
            "knowledge_graph": None  # Optional, can be populated for visualization
        }
    
    def _create_out_of_domain_response(
        self,
        query: str,
        domain: str,
        domain_score: float
    ) -> Dict[str, Any]:
        """Create response for out-of-domain queries."""
        return {
            "answer": f"""I apologize, but your question appears to be outside my area of expertise.

I am a specialized **{domain.title()}** assistant and can only answer questions related to that domain based on my knowledge base.

Your query doesn't seem to match the topics I'm trained on (relevance score: {domain_score*100:.0f}%).

**How I can help:**
- Ask questions related to {domain}
- Query information from my knowledge base
- Get explanations about {domain}-related topics

Would you like to rephrase your question to focus on {domain}?""",
            "confidence": 0.1,
            "in_domain": False,
            "reasoning_paths": [],
            "entities_found": [],
            "explainability": {
                "why_this_answer": {
                    "summary": "Query rejected - outside domain expertise",
                    "sources": []
                },
                "confidence_breakdown": {
                    "overall": "10%",
                    "domain_relevance": f"{domain_score*100:.0f}%",
                    "rejection_reason": "out_of_domain"
                },
                "inputs": {"original_query": query}
            }
        }
    
    def _create_no_results_response(
        self,
        query: str,
        agent: Dict
    ) -> Dict[str, Any]:
        """Create response when no relevant chunks found."""
        return {
            "answer": f"""I couldn't find relevant information in my knowledge base to answer your question.

This could mean:
- The topic isn't covered in my training data
- Try rephrasing your question with different keywords
- Ask about a more specific aspect of {agent.get('domain', 'the domain')}""",
            "confidence": 0.2,
            "in_domain": True,
            "reasoning_paths": [],
            "entities_found": [],
            "explainability": {
                "why_this_answer": {
                    "summary": "No relevant chunks found in knowledge base",
                    "sources": []
                },
                "confidence_breakdown": {
                    "overall": "20%",
                    "issue": "no_relevant_retrieval"
                },
                "inputs": {"original_query": query}
            }
        }


# Factory function
def create_reasoning_engine(data_dir: str = "data/agents") -> ReasoningEngine:
    """Create a new ReasoningEngine instance."""
    return ReasoningEngine(data_dir=data_dir)
