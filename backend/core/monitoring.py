
import logging
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps
from fastapi import Request
import threading

# Configure structured logging
class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)


def setup_logging(json_format: bool = False):
    """Setup logging configuration."""
    logger = logging.getLogger('mexar')
    logger.setLevel(logging.INFO)
    
    # Console handler
    handler = logging.StreamHandler()
    
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    logger.addHandler(handler)
    return logger


# Analytics tracker
class AnalyticsTracker:
    """
    Simple in-memory analytics for tracking usage patterns.
    """
    
    def __init__(self):
        self._metrics = {
            'api_calls': {},
            'chat_messages': 0,
            'compilations': 0,
            'errors': [],
            'response_times': []
        }
        self._lock = threading.RLock()
    
    def track_api_call(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """Track an API call."""
        with self._lock:
            key = f"{method}:{endpoint}"
            if key not in self._metrics['api_calls']:
                self._metrics['api_calls'][key] = {
                    'count': 0,
                    'success': 0,
                    'errors': 0,
                    'avg_duration_ms': 0
                }
            
            self._metrics['api_calls'][key]['count'] += 1
            
            if 200 <= status_code < 400:
                self._metrics['api_calls'][key]['success'] += 1
            else:
                self._metrics['api_calls'][key]['errors'] += 1
            
            # Update rolling average
            current = self._metrics['api_calls'][key]
            current['avg_duration_ms'] = (
                (current['avg_duration_ms'] * (current['count'] - 1) + duration_ms) 
                / current['count']
            )
    
    def track_chat(self):
        """Track a chat message."""
        with self._lock:
            self._metrics['chat_messages'] += 1
    
    def track_compilation(self):
        """Track a compilation."""
        with self._lock:
            self._metrics['compilations'] += 1
    
    def track_error(self, error: str, endpoint: str = None):
        """Track an error."""
        with self._lock:
            self._metrics['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'error': error,
                'endpoint': endpoint
            })
            # Keep only last 100 errors
            if len(self._metrics['errors']) > 100:
                self._metrics['errors'] = self._metrics['errors'][-100:]
    
    def get_stats(self) -> dict:
        """Get current analytics stats."""
        with self._lock:
            total_calls = sum(v['count'] for v in self._metrics['api_calls'].values())
            total_errors = sum(v['errors'] for v in self._metrics['api_calls'].values())
            
            return {
                'total_api_calls': total_calls,
                'total_errors': total_errors,
                'error_rate': total_errors / total_calls if total_calls > 0 else 0,
                'chat_messages': self._metrics['chat_messages'],
                'compilations': self._metrics['compilations'],
                'endpoints': self._metrics['api_calls'],
                'recent_errors': self._metrics['errors'][-10:]
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics = {
                'api_calls': {},
                'chat_messages': 0,
                'compilations': 0,
                'errors': [],
                'response_times': []
            }


# Singleton instance
analytics = AnalyticsTracker()
logger = setup_logging()


# Middleware for request logging and analytics
async def logging_middleware(request: Request, call_next):
    """Log and track all requests."""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Track in analytics
    analytics.track_api_call(
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_ms=duration_ms
    )
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration_ms:.2f}ms"
    )
    
    return response


# Decorator for function-level logging
def log_function(func):
    """Decorator to log function calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {str(e)}")
            analytics.track_error(str(e))
            raise
    return wrapper


async def async_log_function(func):
    """Decorator for async function logging."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {str(e)}")
            analytics.track_error(str(e))
            raise
    return wrapper
