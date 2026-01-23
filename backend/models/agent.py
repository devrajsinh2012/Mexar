from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from core.database import Base


class Agent(Base):
    """AI Agent with all metadata stored in Supabase"""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=True)
    system_prompt = Column(Text, nullable=False)
    
    # All metadata stored in Supabase (no filesystem)
    domain_keywords = Column(JSONB, nullable=True)
    domain_signature = Column(JSONB, nullable=True)
    prompt_analysis = Column(JSONB, nullable=True)
    knowledge_graph_json = Column(JSONB, nullable=True)
    compilation_stats = Column(JSONB, nullable=True)
    
    status = Column(String, default="initializing")  # initializing, compiling, ready, failed
    storage_path = Column(String, nullable=True)  # Deprecated, kept for compatibility
    chunk_count = Column(Integer, default=0)
    entity_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="agents")
    compilation_jobs = relationship("CompilationJob", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="agent", cascade="all, delete-orphan")


class CompilationJob(Base):
    """Background job for agent compilation"""
    __tablename__ = "compilation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="queued")  # queued, processing, completed, failed
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent", back_populates="compilation_jobs")
