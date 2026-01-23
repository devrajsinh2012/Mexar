
from sqlalchemy.orm import Session
from datetime import datetime
from models.user import User
from core.security import get_password_hash, verify_password, create_access_token

class AuthService:
    def register_user(self, db: Session, email: str, password: str) -> User:
        """Register a new user."""
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create user
        hashed_pw = get_password_hash(password)
        new_user = User(email=email, password=hashed_pw)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    def authenticate_user(self, db: Session, email: str, password: str) -> dict:
        """Authenticate user and return token."""
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password):
            return None
        
        # Update login time
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create token
        access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at
            }
        }

    def change_password(self, db: Session, user_email: str, old_password: str, new_password: str):
        """Change user password."""
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise ValueError("User not found")
        
        if not verify_password(old_password, user.password):
            raise ValueError("Incorrect current password")
            
        user.password = get_password_hash(new_password)
        db.commit()
        return True

auth_service = AuthService()
