
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import tempfile
from pathlib import Path

from core.database import get_db
from services.agent_service import agent_service
from services.storage_service import storage_service
from workers.compilation_worker import compilation_worker
from api.deps import get_current_user
from models.user import User

router = APIRouter(prefix="/api/compile", tags=["compile"])

@router.post("/")
async def compile_agent_v2(
    files: List[UploadFile] = File(...),
    agent_name: str = Form(...),
    system_prompt: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compile an agent from uploaded files (Phase 2 - Database integrated).
    
    Creates agent record in database and starts background compilation.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if not agent_name or not agent_name.strip():
        raise HTTPException(status_code=400, detail="Agent name is required")
    if not system_prompt or not system_prompt.strip():
        raise HTTPException(status_code=400, detail="System prompt is required")
    
    try:
        # Create agent record
        agent = agent_service.create_agent(db, current_user, agent_name, system_prompt)
        
        # Read file contents and upload to Supabase
        files_data = []
        for file in files:
            content = await file.read()
            
            # Upload to Supabase Storage (agent-uploads bucket)
            try:
                upload_result = await storage_service.upload_file(
                    file=file,
                    bucket="agent-uploads",
                    folder=f"raw/{agent.id}"
                )
                storage_path = upload_result["path"]
                storage_url = upload_result["url"]
            except Exception as e:
                logger.error(f"Failed to upload raw file to Supabase: {e}")
                storage_path = None
                storage_url = None

            files_data.append({
                "filename": file.filename,
                "content": content.decode("utf-8", errors="ignore"),
                "storage_path": storage_path,
                "storage_url": storage_url
            })
        
        # Start background compilation
        job = compilation_worker.start_compilation(
            db=db,
            agent=agent,
            files_data=files_data
        )
        
        return {
            "success": True,
            "message": f"Compilation started for agent '{agent.name}'",
            "agent_id": agent.id,
            "agent_name": agent.name,
            "job_id": job.id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_name}/status")
def get_compilation_status(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get compilation status for an agent."""
    agent = agent_service.get_agent(db, current_user, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    job_status = compilation_worker.get_job_status(db, agent.id)
    
    if not job_status:
        return {
            "status": agent.status,
            "message": "No compilation job found"
        }
    
    return {
        "agent_status": agent.status,
        "job": job_status
    }
