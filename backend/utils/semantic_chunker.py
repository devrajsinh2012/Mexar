"""
MEXAR - Semantic Chunking Module
Smart chunking that preserves semantic units for better retrieval.
"""
import re
from typing import List, Dict, Any


class SemanticChunker:
    """
    Intelligent text chunking that preserves semantic meaning.
    - Respects paragraph boundaries
    - Groups sentences to target token count
    - Maintains overlap for context continuity
    """
    
    def __init__(self, target_tokens: int = 400, overlap_tokens: int = 50):
        """
        Initialize chunker.
        
        Args:
            target_tokens: Target tokens per chunk (approx 4 chars/token)
            overlap_tokens: Overlap between consecutive chunks
        """
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
    
    def chunk_text(self, text: str, source: str) -> List[Dict[str, Any]]:
        """
        Split unstructured text into semantic chunks.
        
        Args:
            text: Raw text content
            source: Source file name
            
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []
        
        paragraphs = self._split_paragraphs(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._count_tokens(para)
            
            # If adding this paragraph exceeds target and we have content, save chunk
            if current_tokens + para_tokens > self.target_tokens and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append({
                    "content": chunk_text,
                    "source": source,
                    "token_count": current_tokens,
                    "chunk_index": len(chunks)
                })
                
                # Overlap: keep last paragraph for context continuity
                if current_chunk:
                    last_para = current_chunk[-1]
                    current_chunk = [last_para]
                    current_tokens = self._count_tokens(last_para)
                else:
                    current_chunk = []
                    current_tokens = 0
            
            current_chunk.append(para)
            current_tokens += para_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append({
                "content": "\n\n".join(current_chunk),
                "source": source,
                "token_count": current_tokens,
                "chunk_index": len(chunks)
            })
        
        return chunks
    
    def chunk_structured_data(self, data: List[Dict], source: str) -> List[Dict[str, Any]]:
        """
        Convert structured data (CSV/JSON rows) into searchable chunks.
        Each row becomes a self-contained, readable chunk.
        
        Args:
            data: List of dictionaries (rows)
            source: Source file name
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        for i, row in enumerate(data):
            if not isinstance(row, dict):
                continue
            
            # Format row as readable text with context
            content_parts = [f"Entry {i+1} from {source}:"]
            
            for key, value in row.items():
                if value is not None and str(value).strip():
                    # Clean up the key name for readability
                    clean_key = str(key).replace("_", " ").title()
                    content_parts.append(f"  {clean_key}: {value}")
            
            content = "\n".join(content_parts)
            
            chunks.append({
                "content": content,
                "source": f"{source}, Entry {i+1}",
                "token_count": self._count_tokens(content),
                "chunk_index": i,
                "row_data": row  # Keep original data for reference
            })
        
        return chunks
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split on double newlines or multiple newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean and filter empty paragraphs
        cleaned = []
        for p in paragraphs:
            p = p.strip()
            if p:
                cleaned.append(p)
        
        return cleaned
    
    def _count_tokens(self, text: str) -> int:
        """Approximate token count (roughly 4 chars per token)."""
        return len(text.split())


def create_semantic_chunker(target_tokens: int = 400) -> SemanticChunker:
    """Factory function to create a SemanticChunker instance."""
    return SemanticChunker(target_tokens=target_tokens)
