"""
MEXAR Core Engine - Multimodal Input Processing Module
Handles audio, image, and video input conversion to text.
"""

import os
import base64
import logging
import tempfile
from typing import Dict, List, Any, Optional
from pathlib import Path

from utils.groq_client import get_groq_client, GroqClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultimodalProcessor:
    """
    Processes multimodal inputs (audio, image, video) and converts them to text.
    Uses Groq Whisper for audio and Groq Vision for images.
    """
    
    # Supported file types
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm'}
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    
    def __init__(self, groq_client: Optional[GroqClient] = None):
        """
        Initialize the multimodal processor.
        
        Args:
            groq_client: Optional pre-configured Groq client
        """
        self.client = groq_client or get_groq_client()
    
    def process_audio(self, audio_path: str, language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio file using Groq Whisper.
        
        Args:
            audio_path: Path to audio file
            language: Language code for transcription
            
        Returns:
            Dict with transcription results
        """
        path = Path(audio_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if path.suffix.lower() not in self.AUDIO_EXTENSIONS:
            raise ValueError(f"Unsupported audio format: {path.suffix}")
        
        try:
            logger.info(f"Transcribing audio: {path.name}")
            
            transcript = self.client.transcribe_audio(audio_path, language)
            
            return {
                "success": True,
                "type": "audio",
                "file_name": path.name,
                "transcript": transcript,
                "language": language,
                "word_count": len(transcript.split())
            }
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return {
                "success": False,
                "type": "audio",
                "file_name": path.name,
                "error": str(e)
            }
    
    def process_image(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail, including all visible text, objects, and relevant information."
    ) -> Dict[str, Any]:
        """
        Describe image using Groq Vision.
        
        Args:
            image_path: Path to image file
            prompt: Question or instruction for the vision model
            
        Returns:
            Dict with image description
        """
        path = Path(image_path)
        
        if not path.exists():
            logger.error(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if path.suffix.lower() not in self.IMAGE_EXTENSIONS:
            logger.error(f"Unsupported image format: {path.suffix}")
            raise ValueError(f"Unsupported image format: {path.suffix}")
        
        try:
            logger.info(f"Analyzing image: {path.name} (size: {path.stat().st_size} bytes)")
            
            # Call Groq Vision API
            description = self.client.describe_image(image_path, prompt)
            
            logger.info(f"Image analysis successful: {len(description)} chars returned")
            
            return {
                "success": True,
                "type": "image",
                "file_name": path.name,
                "description": description,
                "prompt_used": prompt
            }
            
        except Exception as e:
            logger.error(f"Image analysis failed for {path.name}: {type(e).__name__}: {e}")
            return {
                "success": False,
                "type": "image",
                "file_name": path.name,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def process_video(
        self,
        video_path: str,
        max_frames: int = 5,
        extract_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Process video by extracting keyframes and audio.
        
        Args:
            video_path: Path to video file
            max_frames: Maximum number of keyframes to extract
            extract_audio: Whether to extract and transcribe audio
            
        Returns:
            Dict with video analysis results
        """
        path = Path(video_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if path.suffix.lower() not in self.VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported video format: {path.suffix}")
        
        result = {
            "success": True,
            "type": "video",
            "file_name": path.name,
            "frames": [],
            "audio_transcript": None
        }
        
        try:
            # Try to import OpenCV
            try:
                import cv2
                has_opencv = True
            except ImportError:
                logger.warning("OpenCV not available, skipping video frame extraction")
                has_opencv = False
            
            if has_opencv:
                # Extract keyframes
                frames = self._extract_keyframes(video_path, max_frames)
                
                # Analyze each frame
                for i, frame_path in enumerate(frames):
                    frame_result = self.process_image(
                        frame_path,
                        f"This is frame {i+1} from a video. Describe what you see, focusing on actions, objects, and any text visible."
                    )
                    result["frames"].append(frame_result)
                    
                    # Clean up temp frame
                    try:
                        os.remove(frame_path)
                    except:
                        pass
            
            # Extract and transcribe audio
            if extract_audio:
                audio_path = self._extract_audio(video_path)
                if audio_path:
                    audio_result = self.process_audio(audio_path)
                    result["audio_transcript"] = audio_result.get("transcript", "")
                    
                    # Clean up temp audio
                    try:
                        os.remove(audio_path)
                    except:
                        pass
            
            logger.info(f"Video processed: {len(result['frames'])} frames, audio: {result['audio_transcript'] is not None}")
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    def _extract_keyframes(self, video_path: str, max_frames: int = 5) -> List[str]:
        """Extract keyframes from video using OpenCV."""
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            cap.release()
            return []
        
        # Calculate frame intervals
        interval = max(1, total_frames // max_frames)
        
        frame_paths = []
        frame_count = 0
        
        while cap.isOpened() and len(frame_paths) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % interval == 0:
                # Save frame to temp file
                temp_path = tempfile.mktemp(suffix=".jpg")
                cv2.imwrite(temp_path, frame)
                frame_paths.append(temp_path)
            
            frame_count += 1
        
        cap.release()
        return frame_paths
    
    def _extract_audio(self, video_path: str) -> Optional[str]:
        """Extract audio track from video."""
        try:
            # Try using ffmpeg via subprocess
            import subprocess
            
            temp_audio = tempfile.mktemp(suffix=".mp3")
            
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vn",  # No video
                "-acodec", "libmp3lame",
                "-q:a", "2",
                "-y",  # Overwrite
                temp_audio
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                return temp_audio
            
            return None
            
        except Exception as e:
            logger.warning(f"Audio extraction failed: {e}")
            return None
    
    def fuse_inputs(
        self,
        text: str = "",
        audio_result: Optional[Dict] = None,
        image_result: Optional[Dict] = None,
        video_result: Optional[Dict] = None
    ) -> str:
        """
        Fuse all multimodal inputs into a unified text context.
        
        Args:
            text: Direct text input
            audio_result: Result from process_audio
            image_result: Result from process_image
            video_result: Result from process_video
            
        Returns:
            Unified text context
        """
        context_parts = []
        
        # Add text input
        if text and text.strip():
            context_parts.append(f"[USER TEXT]\n{text.strip()}")
        
        # Add audio transcript
        if audio_result and audio_result.get("success"):
            transcript = audio_result.get("transcript", "")
            if transcript:
                context_parts.append(f"[AUDIO TRANSCRIPT]\n{transcript}")
        
        # Add image description
        if image_result and image_result.get("success"):
            description = image_result.get("description", "")
            if description:
                context_parts.append(f"[IMAGE DESCRIPTION]\n{description}")
        
        # Add video content
        if video_result and video_result.get("success"):
            video_context = []
            
            # Add frame descriptions
            for i, frame in enumerate(video_result.get("frames", [])):
                if frame.get("success"):
                    video_context.append(f"Frame {i+1}: {frame.get('description', '')}")
            
            # Add audio transcript
            if video_result.get("audio_transcript"):
                video_context.append(f"Audio: {video_result['audio_transcript']}")
            
            if video_context:
                context_parts.append(f"[VIDEO ANALYSIS]\n" + "\n".join(video_context))
        
        # Combine all parts
        fused_context = "\n\n".join(context_parts)
        
        logger.info(f"Fused context: {len(fused_context)} characters from {len(context_parts)} sources")
        
        return fused_context
    
    def process_upload(
        self,
        file_path: str,
        additional_text: str = ""
    ) -> Dict[str, Any]:
        """
        Automatically detect file type and process accordingly.
        
        Args:
            file_path: Path to uploaded file
            additional_text: Additional text context
            
        Returns:
            Processing result with fused context
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        
        result = {
            "success": True,
            "file_type": "unknown",
            "processing_result": None,
            "fused_context": ""
        }
        
        try:
            if ext in self.AUDIO_EXTENSIONS:
                result["file_type"] = "audio"
                audio_result = self.process_audio(file_path)
                result["processing_result"] = audio_result
                result["fused_context"] = self.fuse_inputs(
                    text=additional_text,
                    audio_result=audio_result
                )
            
            elif ext in self.IMAGE_EXTENSIONS:
                result["file_type"] = "image"
                image_result = self.process_image(file_path)
                result["processing_result"] = image_result
                result["fused_context"] = self.fuse_inputs(
                    text=additional_text,
                    image_result=image_result
                )
            
            elif ext in self.VIDEO_EXTENSIONS:
                result["file_type"] = "video"
                video_result = self.process_video(file_path)
                result["processing_result"] = video_result
                result["fused_context"] = self.fuse_inputs(
                    text=additional_text,
                    video_result=video_result
                )
            
            else:
                # Treat as text file
                result["file_type"] = "text"
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    file_text = f.read()
                result["fused_context"] = self.fuse_inputs(
                    text=f"{additional_text}\n\n[FILE CONTENT]\n{file_text}"
                )
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            logger.error(f"Upload processing failed: {e}")
        
        return result


# Factory function
def create_multimodal_processor() -> MultimodalProcessor:
    """Create a new MultimodalProcessor instance."""
    return MultimodalProcessor()
