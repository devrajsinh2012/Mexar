
import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Optional
import threading

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

class RateLimiter:
    """
    Simple in-memory rate limiter for API endpoints.
    Uses a sliding window algorithm.
    """
    
    def __init__(self):
        self._requests = defaultdict(list)
        self._lock = threading.RLock()
    
    def is_allowed(
        self, 
        key: str, 
        max_requests: int = 60, 
        window_seconds: int = 60
    ) -> tuple[bool, dict]:
        """
        Check if a request is allowed under rate limits.
        
        Returns: (is_allowed, info_dict)
        """
        with self._lock:
            now = time.time()
            window_start = now - window_seconds
            
            # Clean old requests
            self._requests[key] = [
                t for t in self._requests[key] if t > window_start
            ]
            
            current_count = len(self._requests[key])
            
            if current_count >= max_requests:
                retry_after = self._requests[key][0] - window_start
                return False, {
                    'limit': max_requests,
                    'remaining': 0,
                    'reset': int(self._requests[key][0] + window_seconds),
                    'retry_after': int(retry_after) + 1
                }
            
            # Add current request
            self._requests[key].append(now)
            
            return True, {
                'limit': max_requests,
                'remaining': max_requests - current_count - 1,
                'reset': int(now + window_seconds)
            }
    
    def reset(self, key: str):
        """Reset rate limit for a key."""
        with self._lock:
            if key in self._requests:
                del self._requests[key]


# Singleton instance
rate_limiter = RateLimiter()


# Rate limit configurations per endpoint type
RATE_LIMITS = {
    'auth': {'max_requests': 10, 'window': 60},        # 10 per minute
    'chat': {'max_requests': 30, 'window': 60},        # 30 per minute
    'compile': {'max_requests': 5, 'window': 300},     # 5 per 5 minutes
    'agents': {'max_requests': 60, 'window': 60},      # 60 per minute
    'default': {'max_requests': 100, 'window': 60}     # 100 per minute
}


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting.
    """
    # Get client identifier (IP or user ID if authenticated)
    client_ip = request.client.host if request.client else "unknown"
    
    # Determine endpoint type
    path = request.url.path
    if '/auth/' in path:
        limit_type = 'auth'
    elif '/chat/' in path:
        limit_type = 'chat'
    elif '/compile' in path:
        limit_type = 'compile'
    elif '/agents' in path:
        limit_type = 'agents'
    else:
        limit_type = 'default'
    
    # Check rate limit
    limits = RATE_LIMITS[limit_type]
    key = f"{client_ip}:{limit_type}"
    
    allowed, info = rate_limiter.is_allowed(
        key, 
        max_requests=limits['max_requests'],
        window_seconds=limits['window']
    )
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                'detail': 'Too many requests',
                'retry_after': info['retry_after']
            },
            headers={
                'X-RateLimit-Limit': str(info['limit']),
                'X-RateLimit-Remaining': str(info['remaining']),
                'X-RateLimit-Reset': str(info['reset']),
                'Retry-After': str(info['retry_after'])
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers['X-RateLimit-Limit'] = str(info['limit'])
    response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
    response.headers['X-RateLimit-Reset'] = str(info['reset'])
    
    return response


# File validation constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.csv', '.pdf', '.docx', '.txt', '.json', '.xlsx'}

def validate_file_upload(filename: str, file_size: int) -> Optional[str]:
    """
    Validate an uploaded file.
    Returns error message if invalid, None if valid.
    """
    import os
    
    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"File type '{ext}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check size
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return f"File too large. Maximum size is {max_mb}MB"
    
    return None


# Security headers middleware
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response
