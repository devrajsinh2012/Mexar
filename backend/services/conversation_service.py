
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from models.conversation import Conversation, Message
from models.agent import Agent
from models.user import User

class ConversationService:
    """
    Service for managing conversations and messages.
    Handles auto-creation of conversations and message persistence.
    """
    
    def get_or_create_conversation(
        self, 
        db: Session, 
        agent_id: int, 
        user_id: int
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        conversation = db.query(Conversation).filter(
            Conversation.agent_id == agent_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            conversation = Conversation(
                agent_id=agent_id,
                user_id=user_id
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        return conversation
    
    def add_message(
        self,
        db: Session,
        conversation_id: int,
        role: str,
        content: str,
        multimodal_data: dict = None,
        explainability_data: dict = None,
        confidence: float = None
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            multimodal_data=multimodal_data,
            explainability_data=explainability_data,
            confidence=confidence
        )
        
        db.add(message)
        
        # Update conversation timestamp
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        return message
    
    def get_messages(
        self,
        db: Session,
        conversation_id: int,
        limit: int = 50
    ) -> List[Message]:
        """Get messages from a conversation."""
        return db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.asc()).limit(limit).all()
    
    def get_conversation_history(
        self,
        db: Session,
        agent_id: int,
        user_id: int,
        limit: int = 50
    ) -> List[dict]:
        """Get conversation history for an agent-user pair."""
        conversation = db.query(Conversation).filter(
            Conversation.agent_id == agent_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return []
        
        messages = self.get_messages(db, conversation.id, limit)
        
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "confidence": msg.confidence,
                "explainability": msg.explainability_data
            }
            for msg in messages
        ]
    
    def list_conversations(
        self,
        db: Session,
        user_id: int
    ) -> List[dict]:
        """List all conversations for a user."""
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()
        
        return [
            {
                "id": conv.id,
                "agent_id": conv.agent_id,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "message_count": len(conv.messages)
            }
            for conv in conversations
        ]
    
    def delete_conversation(self, db: Session, conversation_id: int, user_id: int) -> bool:
        """Delete a conversation (with ownership check)."""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return False
        
        db.delete(conversation)
        db.commit()
        return True

# Singleton instance
conversation_service = ConversationService()
