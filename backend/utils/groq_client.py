"""
MEXAR Core Engine - Groq API Client Wrapper
Provides a unified interface for all Groq API interactions.
"""

import os
import base64
from typing import Optional, List, Dict, Any
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GroqClient:
    """
    Unified Groq API client for MEXAR.
    Handles LLM, Whisper (audio), and Vision (image) capabilities.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq client with API key.
        
        Args:
            api_key: Groq API key. If not provided, reads from GROQ_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        
        # Model configurations (using fast model for better conversational responses)
        self.models = {
            "chat": "llama-3.1-8b-instant",  # Primary LLM (fast & conversational)
            "advanced": "llama-3.3-70b-versatile",  # Advanced reasoning
            "fast": "llama-3.1-8b-instant",      # Fast responses
            "vision": "meta-llama/llama-4-scout-17b-16e-instruct",  # Llama 4 Vision model (Jan 2025)
            "whisper": "whisper-large-v3"        # Audio transcription
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "chat",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model key from self.models
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            json_mode: If True, force JSON output
            
        Returns:
            Generated text response
        """
        model_name = self.models.get(model, model)
        
        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    def analyze_with_system_prompt(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "chat",
        json_mode: bool = False
    ) -> str:
        """
        Convenience method for system + user message pattern.
        
        Args:
            system_prompt: System instructions
            user_message: User query
            model: Model to use
            json_mode: If True, force JSON output
            
        Returns:
            Generated response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return self.chat_completion(messages, model=model, json_mode=json_mode)
    
    def transcribe_audio(self, audio_path: str, language: str = "en") -> str:
        """
        Transcribe audio file using Whisper via direct HTTP request.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es')
            
        Returns:
            Transcribed text
        """
        import requests
        from pathlib import Path
        
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        audio_file_path = Path(audio_path)
        
        # Determine the correct mime type
        ext = audio_file_path.suffix.lower()
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".webm": "audio/webm"
        }
        mime_type = mime_types.get(ext, "audio/mpeg")
        
        with open(audio_path, "rb") as audio_file:
            files = {
                "file": (audio_file_path.name, audio_file, mime_type)
            }
            data = {
                "model": "whisper-large-v3-turbo",
                "language": language
            }
            
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("text", "")
        else:
            raise Exception(f"Groq Whisper API error: {response.status_code} - {response.text}")
    
    def describe_image(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail.",
        max_tokens: int = 1024
    ) -> str:
        """
        Describe an image using Vision model.
        
        Args:
            image_path: Path to image file
            prompt: Question about the image
            max_tokens: Maximum response tokens
            
        Returns:
            Image description
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[GROQ VISION] Starting image analysis for: {image_path}")
        logger.info(f"[GROQ VISION] Prompt: {prompt[:100]}...")
        
        # Verify file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file does not exist: {image_path}")
        
        # Get file size
        file_size = os.path.getsize(image_path)
        logger.info(f"[GROQ VISION] Image file size: {file_size} bytes")
        
        # Read and encode image
        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()
            image_data = base64.b64encode(image_bytes).decode("utf-8")
        
        logger.info(f"[GROQ VISION] Image encoded to base64, length: {len(image_data)} chars")
        
        # Detect image type from extension
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        mime_type = mime_types.get(ext, "image/jpeg")
        logger.info(f"[GROQ VISION] Detected MIME type: {mime_type}")
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        logger.info(f"[GROQ VISION] Calling Groq API with model: {self.models['vision']}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.models["vision"],
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            logger.info(f"[GROQ VISION] Success! Response length: {len(result)} chars")
            logger.info(f"[GROQ VISION] Response preview: {result[:200]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"[GROQ VISION] API call failed: {type(e).__name__}: {str(e)}")
            raise
    
    def extract_json(self, text: str, schema_description: str) -> Dict[str, Any]:
        """
        Extract structured JSON from text.
        
        Args:
            text: Input text to analyze
            schema_description: Description of expected JSON structure
            
        Returns:
            Parsed JSON dictionary
        """
        import json
        
        system_prompt = f"""You are a JSON extraction assistant. 
Extract structured data from the given text and return ONLY valid JSON.
Expected structure: {schema_description}
Do not include any explanation, only the JSON object."""
        
        response = self.analyze_with_system_prompt(
            system_prompt=system_prompt,
            user_message=text,
            model="fast",
            json_mode=True
        )
        
        return json.loads(response)


# Singleton instance for easy importing
_client_instance: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get or create the singleton Groq client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = GroqClient()
    return _client_instance
