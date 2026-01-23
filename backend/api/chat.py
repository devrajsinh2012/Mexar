"""
MEXAR Chat API - Phase 2
Handles all chat interactions with agents.
"""

from typing import Optional
from pathlib import Path
import shutil
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from services.agent_service import agent_service
from services.tts_service import get_tts_service
from services.storage_service import storage_service
from services.conversation_service import conversation_service
from api.deps import get_current_user
from models.user import User
from modules.reasoning_engine import create_reasoning_engine
from modules.explainability import create_explainability_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Pydantic models for JSON requests
class ChatRequest(BaseModel):
    agent_name: str
    message: str
    include_explainability: bool = True
    include_tts: bool = False
    tts_provider: str = "elevenlabs"  # "elevenlabs" or "web_speech"


class MultimodalChatRequest(BaseModel):
    agent_name: str
    message: str = ""


class TTSRequest(BaseModel):
    text: str
    provider: str = "elevenlabs"  # "elevenlabs" or "web_speech"
    voice_id: Optional[str] = None


# ===== MAIN CHAT ENDPOINT (JSON) =====

@router.post("")
@router.post("/")
async def chat_json(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with an agent using JSON body.
    This is the primary endpoint used by the frontend.
    """
    # Get agent with ownership check
    agent = agent_service.get_agent(db, current_user, request.agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_name}' not found")
    
    if agent.status != "ready":
        raise HTTPException(
            status_code=400, 
            detail=f"Agent is not ready. Current status: {agent.status}"
        )

    # Get/Create conversation
    conversation = conversation_service.get_or_create_conversation(
        db, agent.id, current_user.id
    )

    # Log USER message
    conversation_service.add_message(
        db, conversation.id, "user", request.message
    )
    
    try:
        # Use agent's storage path for reasoning engine
        storage_path = Path(agent.storage_path).parent
        engine = create_reasoning_engine(str(storage_path))
        
        result = engine.reason(
            agent_name=agent.name,
            query=request.message
        )
        
        response = {
            "success": True,
            "answer": result["answer"],
            "confidence": result["confidence"],
            "in_domain": result["in_domain"]
        }
        
        if request.include_explainability:
            try:
                explainer = create_explainability_generator()
                response["explainability"] = explainer.generate(result)
            except Exception as e:
                logger.warning(f"Explainability generation failed: {e}")
                response["explainability"] = result.get("explainability")
        
        # Log ASSISTANT message
        conversation_service.add_message(
            db, 
            conversation.id, 
            "assistant", 
            result["answer"], 
            explainability_data=response.get("explainability"),
            confidence=result["confidence"]
        )

        # Generate TTS if requested
        if request.include_tts:
            try:
                tts_service = get_tts_service()
                tts_result = tts_service.generate_speech(
                    text=result["answer"],
                    provider=request.tts_provider
                )
                response["tts"] = tts_result
            except Exception as e:
                logger.warning(f"TTS generation failed: {e}")
                response["tts"] = {"success": False, "error": str(e)}
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== MULTIMODAL CHAT ENDPOINT =====

@router.post("/multimodal")
async def chat_multimodal(
    agent_name: str = Form(...),
    message: str = Form(""),
    audio: UploadFile = File(None),
    image: UploadFile = File(None),
    include_explainability: bool = Form(True),
    include_tts: bool = Form(False),
    tts_provider: str = Form("elevenlabs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with an agent using multimodal inputs (audio/image).
    Uses multipart form data.
    """
    from modules.multimodal_processor import create_multimodal_processor
    
    # Get agent with ownership check
    agent = agent_service.get_agent(db, current_user, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    if agent.status != "ready":
        raise HTTPException(
            status_code=400, 
            detail=f"Agent is not ready. Current status: {agent.status}"
        )
    
    # Get/Create conversation
    conversation = conversation_service.get_or_create_conversation(
        db, agent.id, current_user.id
    )

    try:
        multimodal_context = ""
        audio_url = None
        image_url = None
        
        # Process audio if provided
        if audio and audio.filename:
            # Upload to Supabase Storage
            upload_result = await storage_service.upload_file(
                file=audio,
                bucket="chat-media",
                folder=f"audio/{agent.id}"
            )
            audio_url = upload_result["url"]
            
            # Save temporarily for processing
            temp_dir = Path("data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / f"{uuid.uuid4()}{Path(audio.filename).suffix}"
            
            with open(temp_path, "wb") as buffer:
                await audio.seek(0)  # Reset file pointer
                shutil.copyfileobj(audio.file, buffer)
            
            processor = create_multimodal_processor()
            audio_text = processor.process_audio(str(temp_path))
            if audio_text:
                multimodal_context += f"\n[AUDIO TRANSCRIPTION]: {audio_text}"
            
            # Clean up temp file
            try:
                temp_path.unlink()
            except:
                pass
        
        # Process image if provided
        if image and image.filename:
            # Upload to Supabase Storage
            upload_result = await storage_service.upload_file(
                file=image,
                bucket="chat-media",
                folder=f"images/{agent.id}"
            )
            image_url = upload_result["url"]
            logger.info(f"[MULTIMODAL] Image uploaded to Supabase: {image_url}")
            
            # Save temporarily for processing
            temp_dir = Path("data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / f"{uuid.uuid4()}{Path(image.filename).suffix}"
            
            logger.info(f"[MULTIMODAL] Saving temp file: {temp_path}")
            
            with open(temp_path, "wb") as buffer:
                await image.seek(0)  # Reset file pointer
                shutil.copyfileobj(image.file, buffer)
            
            file_size = temp_path.stat().st_size
            logger.info(f"[MULTIMODAL] Temp file saved, size: {file_size} bytes")
            
            try:
                logger.info(f"[MULTIMODAL] Starting image analysis with Groq Vision...")
                processor = create_multimodal_processor()
                image_result = processor.process_image(str(temp_path))
                
                logger.info(f"[MULTIMODAL] Image processing result: {image_result.get('success')}")
                
                if image_result.get("success"):
                    image_desc = image_result.get("description", "")
                    if image_desc:
                        logger.info(f"[MULTIMODAL] ✓ Image analyzed successfully, description length: {len(image_desc)} chars")
                        logger.info(f"[MULTIMODAL] Description preview: {image_desc[:150]}...")
                        multimodal_context += f"\n[IMAGE DESCRIPTION]: {image_desc}"
                    else:
                        logger.warning(f"[MULTIMODAL] Image analysis returned success but empty description")
                        multimodal_context += f"\n[IMAGE]: User uploaded an image named {image.filename}"
                else:
                    # Log error but don't fail - provide basic context
                    error_msg = image_result.get('error', 'Unknown error')
                    error_type = image_result.get('error_type', 'Unknown')
                    logger.warning(f"[MULTIMODAL] Image analysis failed - {error_type}: {error_msg}")
                    multimodal_context += f"\n[IMAGE]: User uploaded an image named {image.filename}"
                    
            except Exception as e:
                logger.error(f"[MULTIMODAL] Image processing exception: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[MULTIMODAL] Traceback: {traceback.format_exc()}")
                multimodal_context += f"\n[IMAGE]: User uploaded an image named {image.filename}"
            
            # Clean up temp file
            try:
                temp_path.unlink()
                logger.info(f"[MULTIMODAL] Temp file cleaned up")
            except:
                pass
        
        # Run reasoning
        storage_path = Path(agent.storage_path).parent
        engine = create_reasoning_engine(str(storage_path))
        
        result = engine.reason(
            agent_name=agent.name,
            query=message,
            multimodal_context=multimodal_context
        )

        # Log USER message with attachments
        conversation_service.add_message(
            db, 
            conversation.id, 
            "user", 
            message,
            multimodal_data={
                "audio_url": audio_url,
                "image_url": image_url
            }
        )
        
        response = {
            "success": True,
            "answer": result["answer"],
            "confidence": result["confidence"],
            "in_domain": result["in_domain"],
            "audio_url": audio_url,
            "image_url": image_url
        }
        
        if include_explainability:
            try:
                explainer = create_explainability_generator()
                response["explainability"] = explainer.generate(result)
            except Exception:
                response["explainability"] = result.get("explainability")
        
        # Log ASSISTANT message
        conversation_service.add_message(
            db, 
            conversation.id, 
            "assistant", 
            result["answer"],
            explainability_data=response.get("explainability"),
            confidence=result["confidence"]
        )

        # Generate TTS if requested
        if include_tts:
            try:
                tts_service = get_tts_service()
                tts_result = tts_service.generate_speech(
                    text=result["answer"],
                    provider=tts_provider
                )
                response["tts"] = tts_result
            except Exception as e:
                logger.warning(f"TTS generation failed: {e}")
                response["tts"] = {"success": False, "error": str(e)}
        
        return response
        
    except Exception as e:
        logger.error(f"Multimodal chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== HISTORY ENDPOINTS =====

@router.get("/{agent_name}/history")
def get_chat_history(
    agent_name: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get conversation history with an agent."""
    from services.conversation_service import conversation_service
    
    agent = agent_service.get_agent(db, current_user, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    history = conversation_service.get_conversation_history(
        db, agent.id, current_user.id, limit
    )
    return {"messages": history}


@router.delete("/{agent_name}/history")
def clear_chat_history(
    agent_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear conversation history with an agent."""
    from models.conversation import Conversation
    
    agent = agent_service.get_agent(db, current_user, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    conversation = db.query(Conversation).filter(
        Conversation.agent_id == agent.id,
        Conversation.user_id == current_user.id
    ).first()
    
    if conversation:
        db.delete(conversation)
        db.commit()
    
    return {"message": "Chat history cleared"}


# ===== TEXT-TO-SPEECH ENDPOINTS =====

@router.post("/tts/generate")
async def generate_tts(
    request: TTSRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate text-to-speech audio."""
    try:
        tts_service = get_tts_service()
        result = tts_service.generate_speech(
            text=request.text,
            provider=request.provider,
            voice_id=request.voice_id
        )
        return result
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tts/audio/{filename}")
async def serve_tts_audio(filename: str):
    """Serve cached TTS audio files."""
    audio_path = Path("data/tts_cache") / filename
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=filename
    )


@router.get("/tts/voices")
async def get_tts_voices(
    provider: str = "elevenlabs",
    current_user: User = Depends(get_current_user)
):
    """Get available TTS voices for a provider."""
    try:
        tts_service = get_tts_service()
        voices = tts_service.get_available_voices(provider)
        return {"provider": provider, "voices": voices}
    except Exception as e:
        logger.error(f"Failed to fetch voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tts/quota")
async def get_tts_quota(current_user: User = Depends(get_current_user)):
    """Check TTS quota for ElevenLabs."""
    try:
        tts_service = get_tts_service()
        quota = tts_service.check_quota()
        return quota
    except Exception as e:
        logger.error(f"Failed to check quota: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== LIVE AUDIO TRANSCRIPTION =====

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    current_user: User = Depends(get_current_user)
):
    """Transcribe uploaded audio (for live recording)."""
    from modules.multimodal_processor import create_multimodal_processor
    
    try:
        # Save audio temporarily
        temp_dir = Path("data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / f"{uuid.uuid4()}{Path(audio.filename).suffix}"
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        
        # Transcribe
        processor = create_multimodal_processor()
        result = processor.process_audio(str(temp_path), language)
        
        # Clean up
        try:
            temp_path.unlink()
        except:
            pass
        
        if result.get("success"):
            return {
                "success": True,
                "transcript": result.get("transcript", ""),
                "language": language,
                "word_count": result.get("word_count", 0)
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Transcription failed"))
        
    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== UTILITY FUNCTIONS =====

async def save_upload(file: UploadFile, base_path: str, subfolder: str) -> str:
    """Save an uploaded file and return its path."""
    upload_dir = Path(base_path) / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    ext = Path(file.filename).suffix
    filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return str(file_path)
