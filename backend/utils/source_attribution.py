"""
MEXAR - Source Attribution Module
Links each sentence in the answer to its supporting source chunk.
Provides inline citations for full transparency.
"""
import re
import logging
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AttributedSentence:
    """A sentence with its source attribution."""
    text: str
    citation: str
    source_chunk_id: int
    source_preview: str
    source_file: str
    similarity: float


@dataclass
class AttributedAnswer:
    """Complete answer with all attributions."""
    answer_with_citations: str
    sentences: List[AttributedSentence]
    sources: List[Dict]


class SourceAttributor:
    """
    Attributes each sentence in an LLM answer to its source chunk.
    
    This enables:
    1. Inline citations [1], [2], etc.
    2. Verification of claims against source data
    3. Transparency about where information came from
    """
    
    def __init__(self, embedding_model=None):
        """
        Initialize attributor.
        
        Args:
            embedding_model: FastEmbed model for sentence embedding
        """
        self.embedding_model = embedding_model
    
    def attribute(
        self, 
        answer: str, 
        chunks: List[Any],
        chunk_embeddings: List[np.ndarray] = None
    ) -> AttributedAnswer:
        """
        Attribute each sentence in answer to source chunks.
        
        Args:
            answer: LLM generated answer
            chunks: Retrieved DocumentChunk objects  
            chunk_embeddings: Pre-computed embeddings (optional)
            
        Returns:
            AttributedAnswer with citations
        """
        if not answer or not chunks:
            return AttributedAnswer(
                answer_with_citations=answer,
                sentences=[],
                sources=[]
            )
        
        # Split answer into sentences
        sentences = self._split_sentences(answer)
        
        # Compute chunk embeddings if not provided
        if chunk_embeddings is None and self.embedding_model:
            contents = [self._get_content(c) for c in chunks]
            chunk_embeddings = list(self.embedding_model.embed(contents))
        
        # Track which sources we've cited
        sources_used = {}  # chunk_id -> citation_number
        attributed_sentences = []
        
        for sentence in sentences:
            # Skip very short or non-substantive sentences
            if len(sentence.split()) < 4:
                continue
            
            # Find best matching chunk
            best_chunk, similarity = self._find_best_source(
                sentence, chunks, chunk_embeddings
            )
            
            # Assign citation number
            chunk_id = self._get_id(best_chunk)
            if chunk_id not in sources_used:
                sources_used[chunk_id] = len(sources_used) + 1
            citation_num = sources_used[chunk_id]
            
            attributed_sentences.append(AttributedSentence(
                text=sentence,
                citation=f"[{citation_num}]",
                source_chunk_id=chunk_id,
                source_preview=self._get_content(best_chunk)[:150],
                source_file=self._get_source(best_chunk),
                similarity=similarity
            ))
        
        # Build answer with inline citations
        answer_with_citations = self._build_cited_answer(answer, attributed_sentences)
        
        # Build sources list for display
        sources = []
        for chunk_id, num in sorted(sources_used.items(), key=lambda x: x[1]):
            # Find the attributed sentence for this chunk
            attr = next((a for a in attributed_sentences if a.source_chunk_id == chunk_id), None)
            if attr:
                sources.append({
                    "citation": f"[{num}]",
                    "chunk_id": chunk_id,
                    "source": attr.source_file,
                    "preview": attr.source_preview,
                    "similarity": round(attr.similarity, 3)
                })
        
        return AttributedAnswer(
            answer_with_citations=answer_with_citations,
            sentences=attributed_sentences,
            sources=sources
        )
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Split on sentence-ending punctuation followed by space
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _find_best_source(
        self, 
        sentence: str, 
        chunks: List[Any],
        chunk_embeddings: List[np.ndarray]
    ) -> Tuple[Any, float]:
        """Find the chunk most similar to the sentence."""
        if not chunks:
            return None, 0.0
        
        # Default to first chunk if no embeddings
        if not self.embedding_model or not chunk_embeddings:
            return chunks[0], 0.5
        
        try:
            # Embed the sentence
            sentence_emb = list(self.embedding_model.embed([sentence]))[0]
            
            # Find best match
            best_chunk = chunks[0]
            best_sim = 0.0
            
            for chunk, emb in zip(chunks, chunk_embeddings):
                sim = self._cosine_similarity(sentence_emb, emb)
                if sim > best_sim:
                    best_sim = sim
                    best_chunk = chunk
            
            return best_chunk, best_sim
            
        except Exception as e:
            logger.warning(f"Embedding failed in attribution: {e}")
            return chunks[0], 0.5
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            dot = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot / (norm_a * norm_b))
        except:
            return 0.0
    
    def _build_cited_answer(
        self, 
        answer: str, 
        attributed: List[AttributedSentence]
    ) -> str:
        """Insert citations after sentences in the answer."""
        result = answer
        
        # Process in reverse order to preserve positions
        for attr in reversed(attributed):
            # Add citation after the sentence
            if attr.text in result:
                result = result.replace(
                    attr.text, 
                    f"{attr.text} {attr.citation}",
                    1  # Only replace first occurrence
                )
        
        return result
    
    def _get_content(self, chunk) -> str:
        """Extract content from chunk object."""
        if hasattr(chunk, 'content'):
            return chunk.content
        elif isinstance(chunk, dict):
            return chunk.get('content', '')
        return str(chunk)
    
    def _get_id(self, chunk) -> int:
        """Extract ID from chunk object."""
        if hasattr(chunk, 'id'):
            return chunk.id
        elif isinstance(chunk, dict):
            return chunk.get('id', 0)
        return 0
    
    def _get_source(self, chunk) -> str:
        """Extract source from chunk object."""
        if hasattr(chunk, 'source'):
            return chunk.source or "unknown"
        elif isinstance(chunk, dict):
            return chunk.get('source', 'unknown')
        return "unknown"


def create_source_attributor(embedding_model=None) -> SourceAttributor:
    """Factory function to create SourceAttributor."""
    return SourceAttributor(embedding_model)
