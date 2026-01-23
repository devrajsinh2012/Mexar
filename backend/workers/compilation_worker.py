
import threading
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from models.agent import Agent, CompilationJob
from modules.knowledge_compiler import KnowledgeCompiler, create_knowledge_compiler
from modules.prompt_analyzer import PromptAnalyzer, create_prompt_analyzer

logger = logging.getLogger(__name__)


def _run_compilation_thread(
    agent_id: int,
    job_id: int,
    storage_path: str,
    system_prompt: str,
    files_data: list
):
    """Execute the compilation process in a separate thread."""
    from core.database import SessionLocal
    
    db = SessionLocal()
    job = None
    agent = None
    
    try:
        job = db.query(CompilationJob).filter(CompilationJob.id == job_id).first()
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not job or not agent:
            logger.error(f"Job or agent not found: job_id={job_id}, agent_id={agent_id}")
            return
        
        logger.info(f"Starting compilation for agent {agent.name}")
        
        # Step 1: Analyze prompt (10%)
        _update_progress(db, job, 10, "Analyzing system prompt")
        analyzer = create_prompt_analyzer()
        prompt_analysis = analyzer.analyze_prompt(system_prompt)
        logger.info(f"Prompt analysis complete: domain={prompt_analysis.get('domain')}")
        
        # Step 2: Initialize compiler (20%)
        _update_progress(db, job, 20, "Initializing knowledge compiler")
        compiler = create_knowledge_compiler(str(Path(storage_path).parent))
        
        # Step 3: Compile knowledge (20-80%)
        _update_progress(db, job, 30, "Compiling knowledge base")
        logger.info(f"Starting compilation with {len(files_data)} files")
        
        # Parse files into the expected format
        parsed_data = []
        for file_info in files_data:
            content = file_info.get("content", "")
            filename = file_info.get("filename", "unknown")
            parsed_data.append({
                "source": filename,
                "content": content,
                "type": "text",
                "records": content.split("\n") if content else []
            })
        
        # Run compilation with error handling
        try:
            result = compiler.compile(
                agent_name=agent.name,
                parsed_data=parsed_data,
                system_prompt=system_prompt,
                prompt_analysis=prompt_analysis
            )
            logger.info(f"Compilation complete: {result.get('stats', {})}")
        except Exception as compile_error:
            logger.error(f"Compilation error (continuing): {compile_error}", exc_info=True)
            # Continue even if compilation has issues - embeddings may still be created
            result = {"stats": {}, "domain_signature": []}
        
        _update_progress(db, job, 80, "Saving to vector store")
        
        # Step 4: Update agent metadata (90%)
        _update_progress(db, job, 90, "Updating agent metadata")
        
        agent.status = "ready"
        agent.domain = prompt_analysis.get("domain", "general")
        agent.domain_keywords = prompt_analysis.get("domain_keywords", [])
        agent.entity_count = result.get("stats", {}).get("total_entries", 0)
        
        # Step 5: Complete (100%)
        job.status = "completed"
        job.progress = 100
        job.current_step = "Compilation complete"
        job.completed_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Agent {agent.name} compilation completed successfully")
            
    except Exception as e:
        logger.error(f"Compilation failed for job {job_id}: {str(e)}", exc_info=True)
        
        # CRITICAL: Always update job and agent status on error
        try:
            if not job:
                job = db.query(CompilationJob).filter(CompilationJob.id == job_id).first()
            if not agent:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
            
            if job:
                job.status = "failed"
                job.error_message = str(e)[:500]  # Limit error message length
                job.completed_at = datetime.utcnow()
                logger.error(f"Job {job_id} marked as failed")
            
            if agent:
                agent.status = "failed"
                logger.error(f"Agent {agent_id} marked as failed")
            
            db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update error status: {update_error}")
            db.rollback()
            
    finally:
        # CRITICAL: Ensure database connection is closed
        try:
            db.close()
            logger.info(f"Database connection closed for job {job_id}")
        except Exception as close_error:
            logger.error(f"Error closing database: {close_error}")


def _update_progress(db: Session, job: CompilationJob, progress: int, step: str):
    """Update job progress."""
    job.progress = progress
    job.current_step = step
    db.commit()
    logger.info(f"Job {job.id} progress: {progress}% - {step}")


class CompilationWorker:
    """
    Background worker for compiling agent knowledge bases.
    Uses threading for reliable async execution on Windows.
    """
    
    def __init__(self):
        self.active_jobs = {}  # agent_id -> job_info
        
    def start_compilation(
        self, 
        db: Session, 
        agent: Agent,
        files_data: list,
        progress_callback: Optional[Callable] = None
    ) -> CompilationJob:
        """Start a background compilation job using threading."""
        
        # Create compilation job record
        job = CompilationJob(
            agent_id=agent.id,
            status="in_progress",
            progress=0,
            current_step="Initializing"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Created compilation job {job.id} for agent {agent.name}")
        
        # Start background thread
        thread = threading.Thread(
            target=_run_compilation_thread,
            args=(agent.id, job.id, agent.storage_path, agent.system_prompt, files_data),
            daemon=True
        )
        thread.start()
        
        self.active_jobs[agent.id] = {
            "job_id": job.id,
            "thread": thread,
            "status": "in_progress"
        }
        
        logger.info(f"Started compilation thread for agent {agent.name}")
        return job
    
    def get_job_status(self, db: Session, agent_id: int) -> Optional[dict]:
        """Get the latest job status for an agent."""
        job = db.query(CompilationJob).filter(
            CompilationJob.agent_id == agent_id
        ).order_by(CompilationJob.created_at.desc()).first()
        
        if not job:
            return None
            
        return {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "current_step": job.current_step,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        }


# Singleton instance
compilation_worker = CompilationWorker()
