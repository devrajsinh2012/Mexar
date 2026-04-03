
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import asyncio
import json

from core.database import get_db, SessionLocal
from services.agent_service import agent_service
from workers.compilation_worker import compilation_worker

router = APIRouter(tags=["websocket"])

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: dict = {}  # agent_name -> list of websockets
    
    async def connect(self, websocket: WebSocket, agent_name: str):
        await websocket.accept()
        if agent_name not in self.active_connections:
            self.active_connections[agent_name] = []
        self.active_connections[agent_name].append(websocket)
    
    def disconnect(self, websocket: WebSocket, agent_name: str):
        if agent_name in self.active_connections:
            if websocket in self.active_connections[agent_name]:
                self.active_connections[agent_name].remove(websocket)
            if not self.active_connections[agent_name]:
                del self.active_connections[agent_name]
    
    async def send_update(self, agent_name: str, data: dict):
        if agent_name in self.active_connections:
            for connection in self.active_connections[agent_name]:
                try:
                    await connection.send_json(data)
                except:
                    pass  # Connection might be closed

manager = ConnectionManager()

@router.websocket("/ws/compile/{agent_name}")
async def websocket_compile_progress(websocket: WebSocket, agent_name: str):
    """WebSocket endpoint for real-time compilation progress."""
    await manager.connect(websocket, agent_name)
    
    try:
        while True:
            # Get current status
            db = SessionLocal()
            try:
                # Find agent by name (without user check for WebSocket)
                from models.agent import Agent
                agent = db.query(Agent).filter(Agent.name == agent_name).first()
                
                if agent:
                    job_status = compilation_worker.get_job_status(db, agent.id)
                    
                    status_data = {
                        "type": "progress",
                        "agent_status": agent.status,
                        "job": job_status
                    }
                    
                    await websocket.send_json(status_data)
                    
                    # Stop polling if complete or failed
                    if agent.status in ["ready", "failed"]:
                        await websocket.send_json({
                            "type": "complete",
                            "agent_status": agent.status
                        })
                        break
            finally:
                db.close()
            
            # Wait before next update
            await asyncio.sleep(1)
            
            # Check for client messages (for keepalive)
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, agent_name)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, agent_name)


@router.websocket("/ws/chat/{agent_name}")
async def websocket_chat(websocket: WebSocket, agent_name: str):
    """WebSocket endpoint for real-time chat (future streaming support)."""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Echo back for now (streaming will be implemented later)
            await websocket.send_json({
                "type": "message",
                "content": f"Received: {message.get('content', '')}"
            })
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Chat WebSocket error: {e}")
