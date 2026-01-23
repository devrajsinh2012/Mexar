"""
MEXAR Agents API - Phase 2  
Handles agent CRUD operations and knowledge graph data.
"""

import json
import logging
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from core.database import get_db
from services.agent_service import agent_service
from api.deps import get_current_user
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ===== PYDANTIC MODELS =====

class AgentCreate(BaseModel):
    name: str
    system_prompt: str


class AgentResponse(BaseModel):
    id: int
    name: str
    status: str
    domain: Optional[str] = None
    entity_count: int
    created_at: datetime
    stats: dict = {}

    model_config = ConfigDict(from_attributes=True)


# ===== LIST AGENTS =====

@router.get("/", response_model=List[AgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all agents owned by the current user."""
    agents = agent_service.list_agents(db, current_user)
    response = []
    
    for agent in agents:
        stats = {}
        if agent.storage_path:
            try:
                metadata_path = Path(agent.storage_path) / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        stats = data.get("stats", {})
            except Exception as e:
                logger.warning(f"Failed to load stats for agent {agent.name}: {e}")
        
        # Convert SQLAlchemy object to dict to include extra fields
        agent_dict = {
            "id": agent.id,
            "name": agent.name,
            "status": agent.status,
            "domain": agent.domain,
            "entity_count": agent.entity_count,
            "created_at": agent.created_at,
            "stats": stats
        }
        response.append(agent_dict)
        
    return response


# ===== CREATE AGENT =====

@router.post("/", response_model=AgentResponse)
def create_agent(
    agent_in: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new agent entry (compilation happens via /api/compile)."""
    try:
        return agent_service.create_agent(
            db, 
            current_user, 
            agent_in.name, 
            agent_in.system_prompt
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== GET AGENT DETAILS =====

@router.get("/{agent_name}")
def get_agent_details(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get full details of an agent including compiled stats."""
    agent = agent_service.get_agent(db, current_user, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Build response with database info
    response = {
        "id": agent.id,
        "name": agent.name,
        "status": agent.status,
        "system_prompt": agent.system_prompt,
        "domain": agent.domain,
        "created_at": agent.created_at,
        "entity_count": agent.entity_count,
        "storage_path": agent.storage_path,
        "stats": {},
        "metadata": {}
    }
    
    # Load compiled metadata for stats
    if agent.storage_path:
        storage_path = Path(agent.storage_path)
        metadata_file = storage_path / "metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                response["metadata"] = metadata
                response["stats"] = metadata.get("stats", {})
            except Exception as e:
                logger.warning(f"Failed to load metadata for {agent_name}: {e}")
    
    return response


# ===== GET KNOWLEDGE GRAPH DATA =====

@router.get("/{agent_name}/graph")
def get_agent_graph(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get knowledge graph data for D3.js visualization.
    
    Returns nodes and links in D3-compatible format.
    """
    agent = agent_service.get_agent(db, current_user, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status != "ready":
        raise HTTPException(
            status_code=400, 
            detail=f"Agent is not ready. Status: {agent.status}"
        )
    
    # Load knowledge graph from file
    storage_path = Path(agent.storage_path)
    graph_file = storage_path / "knowledge_graph.json"
    
    if not graph_file.exists():
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    
    try:
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        # Convert to D3.js format
        nodes = []
        links = []
        node_ids = set()
        
        # Extract nodes from graph data
        if "nodes" in graph_data:
            for node in graph_data["nodes"]:
                node_id = node.get("id", str(node))
                if node_id not in node_ids:
                    nodes.append({
                        "id": node_id,
                        "label": node.get("label", node_id),
                        "type": node.get("type", "entity"),
                        "group": hash(node.get("type", "entity")) % 10
                    })
                    node_ids.add(node_id)
        
        # Extract links/edges
        if "edges" in graph_data:
            for edge in graph_data["edges"]:
                source = edge.get("source", edge.get("from"))
                target = edge.get("target", edge.get("to"))
                if source and target:
                    links.append({
                        "source": source,
                        "target": target,
                        "label": edge.get("relation", edge.get("label", "")),
                        "weight": edge.get("weight", 1)
                    })
        elif "links" in graph_data:
            links = graph_data["links"]
        
        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "node_count": len(nodes),
                "link_count": len(links)
            }
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse knowledge graph: {e}")
        raise HTTPException(status_code=500, detail="Invalid graph data")
    except Exception as e:
        logger.error(f"Error loading graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== GET AGENT EXPLAINABILITY =====

@router.get("/{agent_name}/explainability")
def get_agent_explainability(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get explainability metadata for an agent."""
    agent = agent_service.get_agent(db, current_user, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    storage_path = Path(agent.storage_path)
    metadata_file = storage_path / "metadata.json"
    
    if not metadata_file.exists():
        return {"explainability": None}
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return {
            "agent_name": agent_name,
            "domain": metadata.get("prompt_analysis", {}).get("domain"),
            "domain_signature": metadata.get("domain_signature", []),
            "capabilities": metadata.get("prompt_analysis", {}).get("capabilities", []),
            "stats": metadata.get("stats", {})
        }
    except Exception as e:
        logger.warning(f"Failed to load explainability for {agent_name}: {e}")
        return {"explainability": None}


# ===== DELETE AGENT =====

@router.delete("/{agent_name}")
def delete_agent(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an agent and its files."""
    try:
        agent_service.delete_agent(db, current_user, agent_name)
        return {"message": f"Agent '{agent_name}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
