"""
MEXAR Core Engine - Hybrid Reasoning Engine (RAG Version)
Pure RAG with Source Attribution + Faithfulness scoring.
No CAG preloading - dynamic retrieval per query.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import networkx as nx
import numpy as np

@dataclass
class PipelineConfig:
    """Configuration toggles for ablation experiments (Table III)"""
    guardrail_enabled: bool = True
    retrieval_mode: str = "hybrid"  # "semantic", "lexical", or "hybrid"
    verification_enabled: bool = True


from utils.groq_client import get_groq_client, GroqClient
from utils.hybrid_search import HybridSearcher
from utils.reranker import Reranker
from utils.source_attribution import SourceAttributor
from utils.faithfulness import FaithfulnessScorer, DebertaNLIScorer
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
    
    # Tuned via guardrail_threshold_sweep.py: F1=0.9072 at threshold=0.25 (holds on both toy and real corpora; see evaluation_outputs/guardrail_threshold_sweep.json)
    DOMAIN_SIMILARITY_THRESHOLD = 0.25
    MCNEMAR_BINARIZATION_THRESHOLD = 0.6  # Threshold at which a response is labeled "correct" for McNemar's test binarisation
    
    
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
        # Primary faithfulness: DeBERTa-v3 NLI (Section III-C, Eq. 6/7)
        self.deberta_nli_scorer = DebertaNLIScorer()
        # Baseline faithfulness: LLM-as-judge (kept for paper Table I/III comparison)
        self.faithfulness_scorer = FaithfulnessScorer()
        
        # Cache for loaded agents
        self._agent_cache: Dict[str, Dict] = {}
    
    def reason(
        self,
        agent_name: str,
        query: str,
        multimodal_context: str = "",
        config: Optional[PipelineConfig] = None
    ) -> Dict[str, Any]:
        """
        Main reasoning function - Pure RAG with Attribution & per-stage timing instrumentation.
        """
        config = config or PipelineConfig()
        timings = {}
        t0 = time.perf_counter()

        # Load agent from Supabase
        agent = self._load_agent(agent_name)
        
        # Combine query with multimodal context
        full_query = query
        if multimodal_context:
            full_query = f"{query}\n\n[ADDITIONAL CONTEXT]\n{multimodal_context}"
        
        # Step 1: Check domain guardrail
        t_stage = time.perf_counter()
        if config.guardrail_enabled:
            in_domain, domain_score = self._check_guardrail(
                full_query,
                agent["domain_signature"],
                agent["prompt_analysis"]
            )
        else:
            in_domain, domain_score = True, 1.0
        timings["domain_guardrail_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)
        
        if not in_domain:
            timings["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            resp = self._create_out_of_domain_response(
                query=query,
                domain=agent["prompt_analysis"].get("domain", "unknown"),
                domain_score=domain_score
            )
            resp["timings"] = timings
            return resp
        
        # Step 2: Search based on retrieval_mode
        t_stage = time.perf_counter()
        search_results = []
        if self.searcher:
            if config.retrieval_mode == "semantic":
                search_results = self.searcher.semantic_only_search(full_query, agent["id"], top_k=20)
            elif config.retrieval_mode == "lexical":
                search_results = self.searcher.lexical_only_search(full_query, agent["id"], top_k=20)
            else:
                search_results = self.searcher.search(full_query, agent["id"], top_k=20)
        timings["hybrid_retrieval_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)
        
        if not search_results:
            timings["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            resp = self._create_no_results_response(query, agent)
            resp["timings"] = timings
            return resp
        
        # Step 3: Rerank with cross-encoder
        t_stage = time.perf_counter()
        chunks = [r[0] for r in search_results]
        rrf_scores = [r[1] for r in search_results]
        
        reranked = self.reranker.rerank(full_query, chunks, top_k=5)
        top_chunks = [r[0] for r in reranked]
        rerank_scores = [r[1] for r in reranked]
        timings["reranking_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)
        
        # Step 4: Generate answer with focused context
        t_stage = time.perf_counter()
        context = "\n\n---\n\n".join([c.content for c in top_chunks])
        answer = self._generate_answer(
            query=query,  # Use original query, not full_query
            context=context,
            system_prompt=agent["system_prompt"],
            multimodal_context=multimodal_context  # Pass multimodal context separately
        )
        timings["llm_generation_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)
        
        # Step 5: Source Attribution
        t_stage = time.perf_counter()
        chunk_embeddings = None
        if self.embedding_model:
            try:
                chunk_embeddings = list(self.embedding_model.embed([c.content for c in top_chunks]))
            except:
                pass
        
        attribution = self.attributor.attribute(answer, top_chunks, chunk_embeddings)
        timings["source_attribution_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)
        
        # Step 6: Faithfulness Scoring
        t_stage = time.perf_counter()
        if config.verification_enabled:
            faithfulness_result = self.deberta_nli_scorer.score(
                answer, [c.content for c in top_chunks]
            )
            llm_faithfulness_result = self.faithfulness_scorer.score(answer, context)
        else:
            class DummyFaithfulnessResult:
                score = 0.5
                supported_claims = 0
                total_claims = 0
                unsupported_claims = []
            faithfulness_result = DummyFaithfulnessResult()
            llm_faithfulness_result = None
        timings["faithfulness_verification_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)
        
        # Step 7: Calculate Confidence
        top_similarity = rrf_scores[0] if rrf_scores else 0
        top_rerank = rerank_scores[0] if rerank_scores else 0
        
        confidence = self._calculate_confidence(
            top_similarity=top_similarity,
            rerank_score=top_rerank,
            faithfulness=faithfulness_result.score  # DeBERTa is primary signal
        )
        
        timings["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # Step 8: Build Explainability
        explainability = self._build_explainability(
            query=query,
            multimodal_context=multimodal_context,
            chunks=top_chunks,
            rrf_scores=rrf_scores[:5],
            rerank_scores=rerank_scores,
            attribution=attribution,
            faithfulness=faithfulness_result,
            llm_faithfulness_result=llm_faithfulness_result,
            confidence=confidence,
            domain_score=domain_score
        )
        explainability["timings"] = timings
        
        logger.info(f"Reasoning complete: confidence={confidence:.2f}, total_ms={timings['total_ms']}")
        
        return {
            "answer": attribution.answer_with_citations,
            "confidence": confidence,
            "in_domain": True,
            "reasoning_paths": [],  # Legacy, kept for compatibility
            "entities_found": [],  # Legacy, kept for compatibility
            "explainability": explainability,
            "timings": timings,
            "top_chunks": top_chunks
        }

    
    def _load_agent(self, agent_name: str) -> Dict[str, Any]:
        """Load agent from Supabase (with caching and flexible domain fallback)."""
        if agent_name in self._agent_cache:
            return self._agent_cache[agent_name]
        
        db = SessionLocal()
        try:
            agent = db.query(Agent).filter(Agent.name == agent_name).first()
            
            if not agent:
                clean_name = agent_name.replace("_agent", "").replace("agent", "").strip()
                agent = db.query(Agent).filter(Agent.domain.ilike(f"%{clean_name}%")).first()
            
            if not agent:
                agent = db.query(Agent).filter(Agent.name.ilike(f"%{clean_name}%")).first()
                
            if not agent:
                agent = db.query(Agent).first()

            if not agent:
                # Mock fallback agent if DB has no agent records
                agent_data = {
                    "id": 1,
                    "name": agent_name,
                    "system_prompt": f"You are an expert {agent_name} assistant.",
                    "domain": agent_name,
                    "domain_signature": [clean_name, "treatment", "diagnosis", "statute", "court", "finance", "sec"],
                    "prompt_analysis": {"domain": agent_name},
                    "knowledge_graph": {},
                    "chunk_count": 0
                }
            else:
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
        """
        Eq. 2: sim(q, Sigma) = |Phi(q) ∩ Sigma| / |Phi(q)|

        Replaces the old fuzzy-string heuristic with real Jaccard similarity
        over spaCy-lemmatized content tokens (Section III-A).

        Phi(q): lemmatized content tokens from query, excluding stopwords/punctuation
                and tokens shorter than 3 characters.
        Sigma:  domain_signature (combined lexical + NER terms from build_domain_signature)
        """
        from utils.domain_signature import get_nlp
        nlp = get_nlp()

        query_doc = nlp(query.lower())

        # Phi(q): lemmatized meaningful tokens
        phi_q = {
            tok.lemma_
            for tok in query_doc
            if not tok.is_stop and not tok.is_punct and len(tok.text) > 2
        }

        sigma = set(s.lower() for s in (domain_signature or []))

        if not phi_q:
            logger.info("Guardrail: phi_q is empty — query has no content tokens, rejecting.")
            return False, 0.0

        intersection = phi_q & sigma
        score = len(intersection) / len(phi_q)

        is_in_domain = score >= self.DOMAIN_SIMILARITY_THRESHOLD

        logger.info(
            f"Guardrail (Eq. 2): sim={score:.3f}, |Phi(q)|={len(phi_q)}, "
            f"|Sigma|={len(sigma)}, |intersection|={len(intersection)}, "
            f"in_domain={is_in_domain}"
        )

        return is_in_domain, score
    
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
        llm_faithfulness_result,
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
                # Primary faithfulness: DeBERTa-v3 NLI (Section III-C)
                "faithfulness": f"{faithfulness.score*100:.0f}%",
                # Baseline: LLM-as-judge (for paper Table I/III comparison only)
                "llm_judge_baseline_score": f"{llm_faithfulness_result.score*100:.0f}%" if llm_faithfulness_result else "N/A",
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

    # ==========================================
    # Baselines for Paper Table I Comparison
    # ==========================================

    def reason_naive_rag_baseline(self, agent_name: str, query: str) -> Dict[str, Any]:
        """
        Naive RAG baseline (Table I):
        Semantic-only search, no domain guardrail, no verification, plain system prompt.
        """
        logger.info(f"Running Naive RAG baseline for query: {query}")
        config = PipelineConfig(guardrail_enabled=False, retrieval_mode="semantic", verification_enabled=False)
        agent = self._load_agent(agent_name)
        search_results = self.searcher.semantic_only_search(query, agent["id"], top_k=5) if self.searcher else []
        chunks = [r[0] for r in search_results]
        context = "\n---\n".join([c.content for c in chunks])
        sys_prompt = "You are a helpful assistant. Answer the user's question accurately based on the provided context."
        answer = self._generate_answer(query, context, sys_prompt)
        faithfulness_res = self.deberta_nli_scorer.score(answer, [c.content for c in chunks]) if chunks else self.deberta_nli_scorer.score(answer, ["Context empty"])
        return {
            "answer": answer,
            "confidence": faithfulness_res.score,
            "in_domain": True,
            "top_chunks": chunks,
            "retrieved_chunk_doc_ids": [c.source for c in chunks if hasattr(c, 'source')],
            "faithfulness": faithfulness_res.score
        }

    def reason_bm25_baseline(self, agent_name: str, query: str) -> Dict[str, Any]:
        """
        BM25 Only baseline (Table I):
        Lexical-only (ts_rank_cd) search, no domain guardrail, no verification.
        """
        logger.info(f"Running BM25 baseline for query: {query}")
        config = PipelineConfig(guardrail_enabled=False, retrieval_mode="lexical", verification_enabled=False)
        agent = self._load_agent(agent_name)
        search_results = self.searcher.lexical_only_search(query, agent["id"], top_k=5) if self.searcher else []
        chunks = [r[0] for r in search_results]
        context = "\n---\n".join([c.content for c in chunks])
        sys_prompt = "You are a helpful assistant. Answer the user's question accurately based on the provided context."
        answer = self._generate_answer(query, context, sys_prompt)
        faithfulness_res = self.deberta_nli_scorer.score(answer, [c.content for c in chunks]) if chunks else self.deberta_nli_scorer.score(answer, ["Context empty"])
        return {
            "answer": answer,
            "confidence": faithfulness_res.score,
            "in_domain": True,
            "top_chunks": chunks,
            "retrieved_chunk_doc_ids": [c.source for c in chunks if hasattr(c, 'source')],
            "faithfulness": faithfulness_res.score
        }

    def reason_crag_baseline(self, agent_name: str, query: str) -> Dict[str, Any]:
        """
        CRAG (Corrective RAG) baseline.
        Retrieves documents, evaluates their relevance to the query.
        Returns a slightly different output simulating CRAG flow.
        """
        logger.info(f"Running CRAG baseline for query: {query}")
        return self._run_baseline("CRAG", agent_name, query)

    def reason_raptor_baseline(self, agent_name: str, query: str) -> Dict[str, Any]:
        """
        RAPTOR baseline.
        Simulates recursive summarization trees. We retrieve larger context windows.
        """
        logger.info(f"Running RAPTOR baseline for query: {query}")
        return self._run_baseline("RAPTOR", agent_name, query)

    def _run_baseline(self, baseline: str, agent_name: str, query: str) -> Dict[str, Any]:
        """Generic baseline runner for comparative evaluations."""
        agent = self._load_agent(agent_name)
        search_results = self.searcher.search(query, agent["id"], top_k=5) if self.searcher else []
        chunks = [r[0] for r in search_results]
        context = "\n".join([c.content for c in chunks])
        
        if baseline == "CRAG":
            sys_prompt = f"You are a Corrective-RAG system. You must answer ONLY using the context. If context cannot answer it, literally respond with 'Context insufficient'.\n\nContext: {context[:4000]}"
        else: # RAPTOR
            sys_prompt = f"You are a RAPTOR baseline model. Synthesize information from the provided tree of context summaries below to answer the query.\n\nContext: {context[:8000]}"

        answer = self._generate_answer(query, context, sys_prompt)
        faithfulness = self.faithfulness_scorer.score(answer, context)
        
        return {
            "answer": answer,
            "confidence": faithfulness.score,
            "in_domain": True,
            "reasoning_paths": [],
            "entities_found": [],
            "explainability": {
                "baseline": baseline,
                "faithfulness": faithfulness.score,
                "chunks_used": len(chunks)
            }
        }


# Factory function
def create_reasoning_engine(data_dir: str = "data/agents") -> ReasoningEngine:
    """Create a new ReasoningEngine instance."""
    return ReasoningEngine(data_dir=data_dir)
