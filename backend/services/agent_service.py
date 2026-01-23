
import shutil
import json
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from models.agent import Agent
from models.user import User
from core.config import settings

class AgentService:
    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_agent(self, db: Session, user: User, name: str, system_prompt: str) -> Agent:
        """Create a new agent entry in database."""
        # Sanitize name
        clean_name = name.strip().replace(" ", "_").lower()
        
        # Check if agent already exists for this user
        existing = db.query(Agent).filter(
            Agent.user_id == user.id,
            Agent.name == clean_name
        ).first()
        
        if existing:
            raise ValueError(f"You already have an agent named '{clean_name}'")

        # Create agent storage directory
        agent_dir = self.storage_path / str(user.id) / clean_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DB record
        new_agent = Agent(
            user_id=user.id,
            name=clean_name,
            system_prompt=system_prompt,
            storage_path=str(agent_dir),
            status="initializing"
        )
        
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        return new_agent

    def get_agent(self, db: Session, user: User, agent_name: str) -> Optional[Agent]:
        """Get a specific agent owned by the user."""
        return db.query(Agent).filter(
            Agent.user_id == user.id,
            Agent.name == agent_name
        ).first()

    def get_agent_by_id(self, db: Session, agent_id: int, user_id: int) -> Optional[Agent]:
        """Get agent by ID with ownership check."""
        return db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.user_id == user_id
        ).first()

    def list_agents(self, db: Session, user: User) -> List[Agent]:
        """List all agents owned by the user."""
        return db.query(Agent).filter(Agent.user_id == user.id).all()

    def delete_agent(self, db: Session, user: User, agent_name: str):
        """Delete an agent and its files."""
        agent = self.get_agent(db, user, agent_name)
        if not agent:
            raise ValueError("Agent not found")
            
        # Delete files
        try:
            if agent.storage_path and Path(agent.storage_path).exists():
                shutil.rmtree(agent.storage_path)
        except Exception as e:
            print(f"Error deleting files for agent {agent.name}: {e}")
            # Continue to delete DB record even if file deletion fails
            
        db.delete(agent)
        db.commit()

agent_service = AgentService()
