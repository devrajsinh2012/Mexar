
from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session

from models.agent import Agent
from models.user import User
from services.conversation_service import conversation_service
from modules.reasoning_engine import ReasoningEngine, create_reasoning_engine

class InferenceService:
    """
    Service for running inference with AI agents.
    Wraps the Phase 1 ReasoningEngine with multi-tenancy support.
    """
    
    def __init__(self):
        self.engine_cache = {}  # agent_id -> ReasoningEngine
    
    def get_engine(self, agent: Agent) -> ReasoningEngine:
        """Get or create a reasoning engine for an agent."""
        if agent.id in self.engine_cache:
            return self.engine_cache[agent.id]
        
        # Create new engine
        engine = create_reasoning_engine(agent.storage_path)
        self.engine_cache[agent.id] = engine
        return engine
    
    def clear_cache(self, agent_id: int = None):
        """Clear engine cache."""
        if agent_id:
            if agent_id in self.engine_cache:
                del self.engine_cache[agent_id]
        else:
            self.engine_cache.clear()
    
    def chat(
        self,
        db: Session,
        agent: Agent,
        user: User,
        message: str,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None
    ) -> dict:
        """
        Process a chat message with the agent.
        
        Returns:
            dict with answer, confidence, explainability, etc.
        """
        # Check agent status
        if agent.status != "ready":
            return {
                "answer": f"Agent is not ready. Current status: {agent.status}",
                "confidence": 0.0,
                "in_domain": False,
                "explainability": None
            }
        
        # Get or create conversation
        conversation = conversation_service.get_or_create_conversation(
            db, agent.id, user.id
        )
        
        # Save user message
        conversation_service.add_message(
            db, conversation.id, "user", message,
            multimodal_data={"image": image_path, "audio": audio_path} if image_path or audio_path else None
        )
        
        # Get reasoning engine
        engine = self.get_engine(agent)
        
        # Run inference
        try:
            # Build multimodal context
            multimodal_context = ""
            if image_path:
                multimodal_context += f"[IMAGE: {image_path}]\n"
            if audio_path:
                multimodal_context += f"[AUDIO: {audio_path}]\n"
            
            result = engine.reason(
                agent_name=agent.name,
                query=message,
                multimodal_context=multimodal_context
            )
            
            # Save assistant response
            conversation_service.add_message(
                db, conversation.id, "assistant", result.get("answer", ""),
                explainability_data=result.get("explainability"),
                confidence=result.get("confidence", 0.0)
            )
            
            return result
            
        except Exception as e:
            error_response = {
                "answer": f"Error processing query: {str(e)}",
                "confidence": 0.0,
                "in_domain": False,
                "explainability": None
            }
            
            # Save error response
            conversation_service.add_message(
                db, conversation.id, "assistant", error_response["answer"],
                confidence=0.0
            )
            
            return error_response
    
    def get_history(
        self,
        db: Session,
        agent: Agent,
        user: User,
        limit: int = 50
    ) -> list:
        """Get conversation history for agent-user pair."""
        return conversation_service.get_conversation_history(
            db, agent.id, user.id, limit
        )


# Singleton instance
inference_service = InferenceService()
