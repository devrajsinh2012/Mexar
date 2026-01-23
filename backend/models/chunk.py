from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, mapped_column
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
from core.database import Base


class DocumentChunk(Base):
    """Document chunk with embedding for RAG retrieval"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    section_title = Column(String, nullable=True)
    token_count = Column(Integer, nullable=True)
    
    # 384 dimensions for bge-small-en-v1.5 (unifying for MEXAR Ultimate)
    embedding = mapped_column(Vector(384))
    
    # Full-text search column
    content_tsvector = Column(TSVECTOR)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    agent = relationship("Agent", back_populates="chunks")
