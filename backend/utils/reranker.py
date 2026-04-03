"""
MEXAR - Cross-Encoder Reranking Module
Improves retrieval precision by reranking candidates with a cross-encoder model.
"""
import logging
from typing import List, Tuple, Any

logger = logging.getLogger(__name__)

# Lazy load to avoid slow import on startup
_reranker_model = None


def _get_reranker():
    """Lazy load the cross-encoder model."""
    global _reranker_model
    if _reranker_model is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            logger.info("Cross-encoder reranker loaded successfully")
        except ImportError:
            logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
            _reranker_model = False
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder: {e}")
            _reranker_model = False
    return _reranker_model


class Reranker:
    """
    Cross-encoder reranking for improved retrieval precision.
    
    Cross-encoders are more accurate than bi-encoders because they
    process query and document together, capturing fine-grained interactions.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranker.
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self):
        """Lazy load model on first use."""
        if self._model is None:
            self._model = _get_reranker()
        return self._model
    
    def rerank(
        self, 
        query: str, 
        chunks: List[Any], 
        top_k: int = 5
    ) -> List[Tuple[Any, float]]:
        """
        Rerank chunks using cross-encoder.
        
        Args:
            query: User's query
            chunks: List of DocumentChunk objects
            top_k: Number of top results to return
            
        Returns:
            List of (chunk, score) tuples, sorted by relevance
        """
        if not chunks:
            return []
        
        if not self.model:
            # Fallback: return chunks with placeholder scores
            logger.warning("Reranker not available, using original order")
            return [(chunk, 0.5) for chunk in chunks[:top_k]]
        
        try:
            # Create query-document pairs
            # Truncate content to avoid memory issues
            pairs = [[query, self._get_content(chunk)[:512]] for chunk in chunks]
            
            # Get cross-encoder scores
            scores = self.model.predict(pairs)
            
            # Combine chunks with scores
            chunk_scores = list(zip(chunks, scores))
            
            # Sort by score descending
            ranked = sorted(chunk_scores, key=lambda x: x[1], reverse=True)
            
            logger.info(f"Reranked {len(chunks)} chunks, returning top {top_k}")
            return ranked[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return [(chunk, 0.5) for chunk in chunks[:top_k]]
    
    def _get_content(self, chunk) -> str:
        """Extract content from chunk object."""
        if hasattr(chunk, 'content'):
            return chunk.content
        elif isinstance(chunk, dict):
            return chunk.get('content', '')
        else:
            return str(chunk)


def create_reranker() -> Reranker:
    """Factory function to create Reranker."""
    return Reranker()
