"""
MEXAR Core Engine - Storage Service
Handles file uploads to Supabase Storage.
"""

import os
import logging
from typing import Optional
from pathlib import Path
import uuid
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file uploads to Supabase Storage."""
    
    def __init__(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase Storage client initialized")
    
    async def upload_file(
        self, 
        file: UploadFile, 
        bucket: str, 
        folder: str = ""
    ) -> dict:
        """
        Upload file to Supabase Storage and return file info.
        
        Args:
            file: FastAPI UploadFile object
            bucket: Bucket name (e.g., 'agent-uploads', 'chat-media')
            folder: Optional folder path within bucket
            
        Returns:
            Dict containing:
                - path: File path in storage
                - url: Public URL (if bucket is public)
                - size: File size in bytes
        """
        try:
            # Generate unique filename
            ext = Path(file.filename).suffix
            filename = f"{uuid.uuid4()}{ext}"
            path = f"{folder}/{filename}" if folder else filename
            
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Upload to Supabase
            logger.info(f"Uploading file to {bucket}/{path}")
            response = self.client.storage.from_(bucket).upload(
                path=path,
                file=content,
                file_options={"content-type": file.content_type or "application/octet-stream"}
            )
            
            # Get public URL (works for public buckets)
            public_url = self.client.storage.from_(bucket).get_public_url(path)
            
            logger.info(f"File uploaded successfully: {path}")
            
            return {
                "path": path,
                "url": public_url,
                "size": file_size,
                "bucket": bucket,
                "original_filename": file.filename
            }
            
        except Exception as e:
            logger.error(f"Error uploading file to Supabase Storage: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to upload file: {str(e)}"
            )
    
    def delete_file(self, bucket: str, path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            bucket: Bucket name
            path: File path in bucket
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting file from {bucket}/{path}")
            self.client.storage.from_(bucket).remove([path])
            logger.info(f"File deleted successfully: {path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False
    
    def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        """
        Generate a signed URL for private files.
        
        Args:
            bucket: Bucket name
            path: File path
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Signed URL string
        """
        try:
            response = self.client.storage.from_(bucket).create_signed_url(
                path=path,
                expires_in=expires_in
            )
            return response.get("signedURL", "")
        except Exception as e:
            logger.error(f"Error generating signed URL: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate signed URL: {str(e)}"
            )


# Factory function for easy instantiation
def create_storage_service() -> StorageService:
    """Create a new StorageService instance."""
    return StorageService()


# Global instance
storage_service = create_storage_service()
