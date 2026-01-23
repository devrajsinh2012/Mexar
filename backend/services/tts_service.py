"""
MEXAR Core Engine - Text-to-Speech Service
Provides text-to-speech capabilities with multiple provider support.
"""

import os
import logging
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech service supporting multiple providers:
    - ElevenLabs (high quality, free tier: 10k chars/month)
    - Web Speech API (browser-based, unlimited, handled client-side)
    """
    
    def __init__(self, cache_dir: str = "data/tts_cache"):
        """
        Initialize TTS service.
        
        Args:
            cache_dir: Directory to cache generated audio files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # ElevenLabs configuration
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_base_url = "https://api.elevenlabs.io/v1"
        
        # Default voices
        self.default_voices = {
            "elevenlabs": "21m00Tcm4TlvDq8ikWAM",  # Rachel - neutral
            "web_speech": "default"  # Browser default
        }
    
    def generate_speech(
        self,
        text: str,
        provider: str = "elevenlabs",
        voice_id: Optional[str] = None,
        model_id: str = "eleven_monolingual_v1"
    ) -> Dict[str, Any]:
        """
        Generate speech from text using specified provider.
        
        Args:
            text: Text to convert to speech
            provider: "elevenlabs" or "web_speech"
            voice_id: Voice ID (provider-specific)
            model_id: Model ID for ElevenLabs
            
        Returns:
            Dict with audio file path, provider info, and metadata
        """
        if not text or not text.strip():
            return {
                "success": False,
                "error": "Empty text provided"
            }
        
        # Check cache first
        cache_key = self._get_cache_key(text, provider, voice_id)
        cached_file = self.cache_dir / f"{cache_key}.mp3"
        
        if cached_file.exists():
            logger.info(f"Using cached TTS audio: {cache_key}")
            return {
                "success": True,
                "provider": provider,
                "audio_path": str(cached_file),
                "audio_url": f"/api/chat/tts/audio/{cache_key}.mp3",
                "cached": True,
                "text_length": len(text)
            }
        
        # Generate new audio
        if provider == "elevenlabs":
            return self._generate_elevenlabs(text, voice_id, model_id, cached_file)
        elif provider == "web_speech":
            # Web Speech API is client-side only
            return {
                "success": True,
                "provider": "web_speech",
                "client_side": True,
                "text": text,
                "voice_id": voice_id or self.default_voices["web_speech"],
                "message": "Use browser Web Speech API for playback"
            }
        else:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}"
            }
    
    def _generate_elevenlabs(
        self,
        text: str,
        voice_id: Optional[str],
        model_id: str,
        output_path: Path
    ) -> Dict[str, Any]:
        """Generate speech using ElevenLabs API."""
        if not self.elevenlabs_api_key:
            return {
                "success": False,
                "error": "ElevenLabs API key not configured",
                "fallback": "web_speech"
            }
        
        voice = voice_id or self.default_voices["elevenlabs"]
        
        try:
            url = f"{self.elevenlabs_base_url}/text-to-speech/{voice}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Save audio file
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Generated ElevenLabs TTS: {len(text)} chars")
                
                return {
                    "success": True,
                    "provider": "elevenlabs",
                    "audio_path": str(output_path),
                    "audio_url": f"/api/chat/tts/audio/{output_path.name}",
                    "cached": False,
                    "text_length": len(text),
                    "voice_id": voice
                }
            
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "Invalid ElevenLabs API key",
                    "fallback": "web_speech"
                }
            
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "ElevenLabs quota exceeded",
                    "fallback": "web_speech"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"ElevenLabs API error: {response.status_code}",
                    "fallback": "web_speech"
                }
        
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "web_speech"
            }
    
    def get_available_voices(self, provider: str = "elevenlabs") -> List[Dict[str, str]]:
        """
        Get list of available voices for a provider.
        
        Args:
            provider: "elevenlabs" or "web_speech"
            
        Returns:
            List of voice dictionaries with id, name, and metadata
        """
        if provider == "elevenlabs":
            if not self.elevenlabs_api_key:
                return []
            
            try:
                url = f"{self.elevenlabs_base_url}/voices"
                headers = {"xi-api-key": self.elevenlabs_api_key}
                
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "id": voice["voice_id"],
                            "name": voice["name"],
                            "category": voice.get("category", "general"),
                            "preview_url": voice.get("preview_url")
                        }
                        for voice in data.get("voices", [])
                    ]
                
            except Exception as e:
                logger.error(f"Failed to fetch ElevenLabs voices: {e}")
                return []
        
        elif provider == "web_speech":
            # Web Speech API voices are browser-specific
            return [
                {"id": "default", "name": "Browser Default", "category": "system"}
            ]
        
        return []
    
    def check_quota(self) -> Dict[str, Any]:
        """
        Check remaining quota for ElevenLabs.
        
        Returns:
            Dict with quota information
        """
        if not self.elevenlabs_api_key:
            return {
                "provider": "elevenlabs",
                "configured": False
            }
        
        try:
            url = f"{self.elevenlabs_base_url}/user"
            headers = {"xi-api-key": self.elevenlabs_api_key}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                subscription = data.get("subscription", {})
                
                return {
                    "provider": "elevenlabs",
                    "configured": True,
                    "character_count": subscription.get("character_count", 0),
                    "character_limit": subscription.get("character_limit", 10000),
                    "remaining": subscription.get("character_limit", 10000) - subscription.get("character_count", 0),
                    "tier": subscription.get("tier", "free")
                }
            
        except Exception as e:
            logger.error(f"Failed to check ElevenLabs quota: {e}")
        
        return {
            "provider": "elevenlabs",
            "configured": True,
            "error": "Failed to fetch quota"
        }
    
    def _get_cache_key(self, text: str, provider: str, voice_id: Optional[str]) -> str:
        """Generate cache key for audio file."""
        content = f"{provider}:{voice_id or 'default'}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self) -> int:
        """
        Clear all cached audio files.
        
        Returns:
            Number of files deleted
        """
        count = 0
        for file in self.cache_dir.glob("*.mp3"):
            try:
                file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache file {file}: {e}")
        
        logger.info(f"Cleared {count} cached TTS files")
        return count


# Singleton instance
_tts_service_instance: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create the singleton TTS service instance."""
    global _tts_service_instance
    if _tts_service_instance is None:
        _tts_service_instance = TTSService()
    return _tts_service_instance
