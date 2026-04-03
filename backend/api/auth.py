
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel, EmailStr
from core.database import get_db
from services.auth_service import auth_service
from api.deps import get_current_user
from models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class UserPreferences(BaseModel):
    tts_provider: str = "elevenlabs"
    auto_play_tts: bool = False
    other: Optional[Dict[str, Any]] = {}

@router.post("/register", response_model=dict)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        user = auth_service.register_user(db, user_in.email, user_in.password)
        return {"message": "User registered successfully", "id": user.id, "email": user.email}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """Login and get token"""
    result = auth_service.authenticate_user(db, user_in.email, user_in.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user data"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "preferences": current_user.preferences or {}
    }

@router.put("/preferences")
def update_preferences(
    prefs: UserPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    # Initialize defaults if None
    current_prefs = dict(current_user.preferences) if current_user.preferences else {}
    
    # Update values
    current_prefs["tts_provider"] = prefs.tts_provider
    current_prefs["auto_play_tts"] = prefs.auto_play_tts
    if prefs.other:
        current_prefs.update(prefs.other)
        
    current_user.preferences = current_prefs
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Preferences updated", "preferences": current_user.preferences}

@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        auth_service.change_password(
            db, 
            current_user.email, 
            password_data.old_password, 
            password_data.new_password
        )
        return {"message": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
