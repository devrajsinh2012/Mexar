"""
MEXAR - Hybrid Search Module
Combines semantic (vector) search with keyword (full-text) search using RRF.
"""
import logging
from typing import List, Tuple, Optional
from sqlalchemy import text
from core.database import SessionLocal
from models.chunk import DocumentChunk

logger = logging.getLogger(__name__)


class HybridSearcher:
    """
    Hybrid search combining:
    1. Semantic search (pgvector cosine similarity)
    2. Keyword search (PostgreSQL tsvector)
    3. Reciprocal Rank Fusion (RRF) to merge results
    """
    
    def __init__(self, embedding_model):
        """
        Initialize hybrid searcher.
        
        Args:
            embedding_model: FastEmbed model for query embedding
        """
        self.embedding_model = embedding_model
    
    def search(
        self, 
        query: str, 
        agent_id: int, 
        top_k: int = 20
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Perform hybrid search using Supabase RPC function.
        
        Args:
            query: User's search query
            agent_id: ID of the agent to search within
            top_k: Number of results to return
            
        Returns:
            List of (DocumentChunk, rrf_score) tuples
        """
        if not query.strip():
            return []
        
        try:
            # Generate query embedding
            query_embedding = list(self.embedding_model.embed([query]))[0].tolist()
            
            db = SessionLocal()
            try:
                # Call the hybrid_search function created in migration
                # Use CAST syntax to avoid clashing with SQLAlchemy bind parameters (:: is often parsed as a parameter)
                result = db.execute(text("""
                    SELECT * FROM hybrid_search(
                        CAST(:embedding AS vector),
                        :query_text,
                        :agent_id,
                        :match_count
                    )
                """), {
                    "embedding": query_embedding,
                    "query_text": query,
                    "agent_id": agent_id,
                    "match_count": top_k
                })
                
                rows = result.fetchall()
                
                if not rows:
                    # Fallback to pure semantic search if hybrid returns nothing
                    return self._semantic_only_search(db, query_embedding, agent_id, top_k)
                
                # Fetch full chunk objects
                chunk_ids = [row.id for row in rows]
                chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(chunk_ids)
                ).all()
                chunk_map = {c.id: c for c in chunks}
                
                # Return chunks with RRF scores, maintaining order
                results = []
                for row in rows:
                    if row.id in chunk_map:
                        results.append((chunk_map[row.id], row.rrf_score))
                
                logger.info(f"Hybrid search found {len(results)} results for agent {agent_id}")
                return results
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            # Fallback to simple semantic search
            return self._fallback_semantic_search(query, agent_id, top_k)
    
    def _semantic_only_search(
        self, 
        db, 
        query_embedding: List[float], 
        agent_id: int, 
        top_k: int
    ) -> List[Tuple[DocumentChunk, float]]:
        """Pure semantic search fallback."""
        try:
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.agent_id == agent_id
            ).order_by(
                DocumentChunk.embedding.cosine_distance(query_embedding)
            ).limit(top_k).all()
            
            # Calculate similarity scores (1 - distance)
            results = []
            for i, chunk in enumerate(chunks):
                # Approximate score based on rank
                score = 1.0 / (1 + i * 0.1)
                results.append((chunk, score))
            
            return results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _fallback_semantic_search(
        self, 
        query: str, 
        agent_id: int, 
        top_k: int
    ) -> List[Tuple[DocumentChunk, float]]:
        """Fallback when hybrid search function not available."""
        try:
            query_embedding = list(self.embedding_model.embed([query]))[0].tolist()
            
            db = SessionLocal()
            try:
                return self._semantic_only_search(db, query_embedding, agent_id, top_k)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []


def create_hybrid_searcher(embedding_model) -> HybridSearcher:
    """Factory function to create HybridSearcher."""
    return HybridSearcher(embedding_model)
