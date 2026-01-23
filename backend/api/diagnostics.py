"""
Compilation Health Monitoring API

Provides endpoints to monitor compilation job health and detect issues.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from core.database import get_db
from api.deps import get_current_user
from models.user import User
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

@router.get("/compilation-health")
def get_compilation_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall compilation health status.
    Shows active jobs, stuck jobs, and recent failures.
    """
    
    # Active jobs
    active_result = db.execute(text("""
        SELECT COUNT(*) as count
        FROM compilation_jobs cj
        JOIN agents a ON cj.agent_id = a.id
        WHERE cj.status = 'in_progress'
        AND a.user_id = :user_id
    """), {"user_id": current_user.id})
    active_count = active_result.fetchone().count
    
    # Stuck jobs (running > 30 minutes)
    stuck_result = db.execute(text("""
        SELECT 
            cj.id,
            a.name as agent_name,
            cj.progress,
            cj.current_step,
            EXTRACT(EPOCH FROM (NOW() - cj.created_at)) / 60 as minutes_running
        FROM compilation_jobs cj
        JOIN agents a ON cj.agent_id = a.id
        WHERE cj.status = 'in_progress'
        AND a.user_id = :user_id
        AND cj.created_at < NOW() - INTERVAL '30 minutes'
    """), {"user_id": current_user.id})
    stuck_jobs = stuck_result.fetchall()
    
    # Recent failures (last 24 hours)
    failed_result = db.execute(text("""
        SELECT 
            a.name as agent_name,
            cj.error_message,
            cj.created_at
        FROM compilation_jobs cj
        JOIN agents a ON cj.agent_id = a.id
        WHERE cj.status = 'failed'
        AND a.user_id = :user_id
        AND cj.created_at > NOW() - INTERVAL '24 hours'
        ORDER BY cj.created_at DESC
        LIMIT 5
    """), {"user_id": current_user.id})
    recent_failures = failed_result.fetchall()
    
    # Success rate (last 24 hours)
    stats_result = db.execute(text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM compilation_jobs cj
        JOIN agents a ON cj.agent_id = a.id
        WHERE a.user_id = :user_id
        AND cj.created_at > NOW() - INTERVAL '24 hours'
    """), {"user_id": current_user.id})
    stats = stats_result.fetchone()
    
    success_rate = (stats.completed / stats.total * 100) if stats.total > 0 else 0
    
    return {
        "status": "healthy" if len(stuck_jobs) == 0 else "warning",
        "active_jobs": active_count,
        "stuck_jobs": [
            {
                "id": job.id,
                "agent_name": job.agent_name,
                "progress": job.progress,
                "current_step": job.current_step,
                "minutes_running": round(job.minutes_running, 1)
            }
            for job in stuck_jobs
        ],
        "recent_failures": [
            {
                "agent_name": f.agent_name,
                "error": f.error_message,
                "created_at": f.created_at.isoformat()
            }
            for f in recent_failures
        ],
        "stats_24h": {
            "total_jobs": stats.total,
            "completed": stats.completed,
            "failed": stats.failed,
            "success_rate": round(success_rate, 1)
        }
    }

@router.get("/embedding-model-status")
def get_embedding_model_status():
    """Check if the embedding model is working"""
    try:
        from fastembed import TextEmbedding
        
        model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        test_text = ["Test sentence"]
        embeddings = list(model.embed(test_text))
        
        return {
            "status": "healthy",
            "model": "BAAI/bge-small-en-v1.5",
            "dimension": len(embeddings[0]),
            "message": "Embedding model is working correctly"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
