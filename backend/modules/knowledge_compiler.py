"""
MEXAR Core Engine - Knowledge Compilation Module
Builds Vector embeddings from parsed data for semantic retrieval.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from utils.groq_client import get_groq_client, GroqClient
from fastembed import TextEmbedding
from core.database import SessionLocal
from models.agent import Agent
from models.chunk import DocumentChunk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeCompiler:
    """
    Compiles knowledge from parsed data into Vector embeddings.
    Uses semantic similarity for retrieval-based reasoning.
    """
    
    def __init__(self, groq_client: Optional[GroqClient] = None, data_dir: str = "data/agents"):
        """
        Initialize the knowledge compiler.
        
        Args:
            groq_client: Optional pre-configured Groq client
            data_dir: Directory to store agent data
        """
        self.client = groq_client or get_groq_client()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Compilation progress tracking
        self.progress = {
            "status": "idle",
            "percentage": 0,
            "current_step": "",
            "details": {}
        }
        
        # Initialize embedding model (384 dim default)
        try:
            # Force cache to /tmp for HF Spaces or use env var
            cache_dir = os.getenv("FASTEMBED_CACHE_PATH", "/tmp/.cache/fastembed")
            self.embedding_model = TextEmbedding(
                model_name="BAAI/bge-small-en-v1.5", 
                cache_dir=cache_dir
            )
            logger.info(f"FastEmbed model loaded (cache: {cache_dir})")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            self.embedding_model = None
    
    def compile(
        self,
        agent_name: str,
        parsed_data: List[Dict[str, Any]],
        system_prompt: str,
        prompt_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main compilation function.
        
        Args:
            agent_name: Name of the agent being created
            parsed_data: List of parsed file results from DataValidator
            system_prompt: User's system prompt
            prompt_analysis: Analysis from PromptAnalyzer
            
        Returns:
            Dict containing:
                - domain_signature: Keywords for domain matching
                - stats: Compilation statistics
        """
        self._update_progress("starting", 0, "Initializing compilation...")
        
        try:
            # Step 1: Build text context (30%)
            self._update_progress("building_context", 10, "Building text context...")
            text_context = self._build_text_context(parsed_data)
            self._update_progress("building_context", 30, f"Text context built: {len(text_context):,} characters")
            
            # Step 2: Extract domain signature (50%)
            self._update_progress("extracting_signature", 35, "Extracting domain signature...")
            domain_signature = self._extract_domain_signature(parsed_data, prompt_analysis)
            self._update_progress("extracting_signature", 50, f"Domain signature: {len(domain_signature)} keywords")
            
            # Step 3: Calculate stats (60%)
            self._update_progress("calculating_stats", 55, "Calculating statistics...")
            stats = self._calculate_stats(text_context, parsed_data)
            
            # Step 4: Save metadata (70%)
            self._update_progress("saving", 65, "Saving agent metadata...")
            self._save_agent(
                agent_name=agent_name,
                text_context=text_context,
                domain_signature=domain_signature,
                system_prompt=system_prompt,
                prompt_analysis=prompt_analysis,
                stats=stats
            )
            
            # Step 5: Save to Vector DB (95%)
            if self.embedding_model:
                self._update_progress("saving_vector", 75, "Saving to Vector Store...")
                self._save_to_vector_db(agent_name, text_context)
            
            self._update_progress("complete", 100, "Compilation complete!")
            
            return {
                "domain_signature": domain_signature,
                "stats": stats,
                "agent_path": str(self.data_dir / agent_name)
            }
            
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            self._update_progress("error", self.progress["percentage"], f"Error: {str(e)}")
            raise
    
    def _update_progress(self, status: str, percentage: int, step: str, details: Dict = None):
        """Update compilation progress."""
        self.progress = {
            "status": status,
            "percentage": percentage,
            "current_step": step,
            "details": details or {}
        }
        logger.info(f"[{percentage}%] {step}")
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current compilation progress."""
        return self.progress.copy()
    
    def _build_text_context(self, parsed_data: List[Dict[str, Any]]) -> str:
        """
        Build text context from parsed data.
        
        Args:
            parsed_data: Parsed file data
            
        Returns:
            Formatted text context
        """
        context_parts = []
        
        for i, file_data in enumerate(parsed_data):
            file_name = file_data.get("file_name", file_data.get("source", f"Source_{i+1}"))
            file_format = file_data.get("format", file_data.get("type", "unknown"))
            
            context_parts.append(f"\n{'='*60}")
            context_parts.append(f"SOURCE: {file_name} ({file_format.upper()})")
            context_parts.append(f"{'='*60}\n")
            
            # Handle structured data (CSV, JSON)
            if file_data.get("data"):
                for j, entry in enumerate(file_data["data"]):
                    if isinstance(entry, dict):
                        entry_lines = [f"[Entry {j+1}]"]
                        for key, value in entry.items():
                            if value is not None and str(value).strip():
                                entry_lines.append(f"  {key}: {value}")
                        context_parts.append("\n".join(entry_lines))
                    else:
                        context_parts.append(f"[Entry {j+1}] {entry}")
            
            # Handle unstructured text (PDF, DOCX, TXT)
            elif file_data.get("text"):
                context_parts.append(file_data["text"])
            
            # Handle content field
            elif file_data.get("content"):
                context_parts.append(file_data["content"])
            
            # Handle records field
            elif file_data.get("records"):
                for j, record in enumerate(file_data["records"]):
                    if record and record.strip():
                        context_parts.append(f"[Line {j+1}] {record}")
        
        text_context = "\n".join(context_parts)
        
        # Limit to prevent token overflow (approximately 128K tokens = 500K chars)
        max_chars = 500000
        if len(text_context) > max_chars:
            logger.warning(f"Text context truncated from {len(text_context)} to {max_chars} characters")
            text_context = text_context[:max_chars] + "\n\n[CONTEXT TRUNCATED DUE TO SIZE LIMITS]"
        
        return text_context
    
    def _extract_domain_signature(
        self,
        parsed_data: List[Dict[str, Any]],
        prompt_analysis: Dict[str, Any]
    ) -> List[str]:
        """
        Extract domain signature keywords for guardrail checking.
        """
        # Start with analyzed keywords (highest priority)
        domain_keywords = prompt_analysis.get("domain_keywords", [])
        signature = list(domain_keywords)
        
        # Add domain and sub-domains
        domain = prompt_analysis.get("domain", "")
        if domain and domain not in signature:
            signature.insert(0, domain)
        
        for sub_domain in prompt_analysis.get("sub_domains", []):
            if sub_domain and sub_domain.lower() not in [s.lower() for s in signature]:
                signature.append(sub_domain)
        
        # Extract column headers from structured data
        for file_data in parsed_data:
            if file_data.get("data") and isinstance(file_data["data"], list):
                if file_data["data"] and isinstance(file_data["data"][0], dict):
                    for key in file_data["data"][0].keys():
                        clean_key = key.lower().strip().replace("_", " ")
                        if clean_key and clean_key not in [s.lower() for s in signature]:
                            signature.append(clean_key)
        
        return signature[:80]  # Limit for efficiency
    
    def _calculate_stats(
        self,
        text_context: str,
        parsed_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate compilation statistics."""
        return {
            "context_length": len(text_context),
            "context_tokens": len(text_context) // 4,  # Rough estimate
            "source_files": len(parsed_data),
            "total_entries": sum(
                len(p.get("data", [])) or len(p.get("records", []))
                for p in parsed_data
            )
        }
    
    def _save_agent(
        self,
        agent_name: str,
        text_context: str,
        domain_signature: List[str],
        system_prompt: str,
        prompt_analysis: Dict[str, Any],
        stats: Dict[str, Any]
    ):
        """Save agent artifacts to filesystem."""
        agent_dir = self.data_dir / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Save text context (for backup/debugging)
        with open(agent_dir / "context.txt", "w", encoding="utf-8") as f:
            f.write(text_context)
        
        # Save metadata
        metadata = {
            "agent_name": agent_name,
            "system_prompt": system_prompt,
            "prompt_analysis": prompt_analysis,
            "domain_signature": domain_signature,
            "stats": stats,
            "created_at": self._get_timestamp()
        }
        with open(agent_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Agent saved to: {agent_dir}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def load_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Load a previously compiled agent.
        
        Args:
            agent_name: Name of the agent to load
            
        Returns:
            Dict with agent artifacts
        """
        agent_dir = self.data_dir / agent_name
        
        if not agent_dir.exists():
            raise FileNotFoundError(f"Agent '{agent_name}' not found")
        
        # Load metadata
        with open(agent_dir / "metadata.json", "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        return {
            "metadata": metadata,
            "domain_signature": metadata.get("domain_signature", []),
            "system_prompt": metadata.get("system_prompt", ""),
            "prompt_analysis": metadata.get("prompt_analysis", {})
        }
    
    def _save_to_vector_db(self, agent_name: str, context: str):
        """Chunk and save context to vector database."""
        try:
            chunks = self._chunk_text(context)
            if not chunks:
                logger.warning(f"No chunks generated for {agent_name}")
                return

            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            
            # Generate embeddings with error handling
            try:
                embeddings = list(self.embedding_model.embed(chunks))
                logger.info(f"Successfully generated {len(embeddings)} embeddings")
            except Exception as embed_error:
                logger.error(f"Embedding generation failed: {embed_error}")
                # Don't fail the entire compilation if embeddings fail
                return
            
            with SessionLocal() as db:
                agent = db.query(Agent).filter(Agent.name == agent_name).first()
                if not agent:
                    logger.error(f"Agent {agent_name} not found in DB")
                    return
                
                # Clear old chunks
                try:
                    deleted_count = db.query(DocumentChunk).filter(DocumentChunk.agent_id == agent.id).delete()
                    logger.info(f"Deleted {deleted_count} old chunks for agent {agent_name}")
                except Exception as delete_error:
                    logger.warning(f"Failed to delete old chunks: {delete_error}")
                    # Continue anyway
                
                # Insert new chunks
                try:
                    new_chunks = [
                        DocumentChunk(
                            agent_id=agent.id,
                            content=chunk,
                            embedding=embedding.tolist(),
                            source="context"
                        )
                        for chunk, embedding in zip(chunks, embeddings)
                    ]
                    db.add_all(new_chunks)
                    
                    # Update agent's chunk_count
                    agent.chunk_count = len(new_chunks)
                    
                    db.commit()
                    logger.info(f"Saved {len(new_chunks)} chunks to vector store for {agent_name}")
                except Exception as insert_error:
                    logger.error(f"Failed to insert chunks: {insert_error}")
                    db.rollback()
                    raise
                
        except Exception as e:
            logger.error(f"Vector save failed: {e}", exc_info=True)
            # Don't raise - allow compilation to continue even if vector save fails


    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Simple text chunker."""
        chunks = []
        if not text:
            return []
        
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start += (chunk_size - overlap)
        return chunks

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all compiled agents."""
        agents = []
        
        for agent_dir in self.data_dir.iterdir():
            if agent_dir.is_dir():
                metadata_path = agent_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    agents.append({
                        "name": agent_dir.name,
                        "domain": metadata.get("prompt_analysis", {}).get("domain", "unknown"),
                        "created_at": metadata.get("created_at"),
                        "stats": metadata.get("stats", {})
                    })
        
        return agents


# Factory function
def create_knowledge_compiler(data_dir: str = "data/agents") -> KnowledgeCompiler:
    """Create a new KnowledgeCompiler instance."""
    return KnowledgeCompiler(data_dir=data_dir)
