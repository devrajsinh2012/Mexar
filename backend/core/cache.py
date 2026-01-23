
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import threading

class InMemoryCache:
    """
    Simple in-memory cache with TTL support.
    Replaces Redis for development environments.
    """
    
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, dict] = {}
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry['expires_at'] and datetime.utcnow() > entry['expires_at']:
                del self._cache[key]
                return None
            
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set a value in cache with optional TTL."""
        with self._lock:
            ttl = ttl if ttl is not None else self._default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None
            
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.utcnow()
            }
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            now = datetime.utcnow()
            active = sum(1 for e in self._cache.values() 
                        if not e['expires_at'] or e['expires_at'] > now)
            return {
                'total_keys': len(self._cache),
                'active_keys': active,
                'expired_keys': len(self._cache) - active
            }
    
    def cleanup(self) -> int:
        """Remove expired entries and return count removed."""
        with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                k for k, v in self._cache.items() 
                if v['expires_at'] and v['expires_at'] < now
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


# Singleton instance
cache = InMemoryCache(default_ttl=3600)  # 1 hour default


# Helper functions for common caching patterns
def cache_agent_artifacts(agent_id: int, artifacts: dict, ttl: int = 3600):
    """Cache agent artifacts (knowledge graph, etc.)"""
    cache.set(f"agent:{agent_id}:artifacts", artifacts, ttl)

def get_cached_agent_artifacts(agent_id: int) -> Optional[dict]:
    """Get cached agent artifacts."""
    return cache.get(f"agent:{agent_id}:artifacts")

def invalidate_agent_cache(agent_id: int):
    """Invalidate all cache entries for an agent."""
    cache.delete(f"agent:{agent_id}:artifacts")
    cache.delete(f"agent:{agent_id}:engine")

def cache_user_agents(user_id: int, agents: list, ttl: int = 60):
    """Cache user's agent list for quick dashboard loading."""
    cache.set(f"user:{user_id}:agents", agents, ttl)

def get_cached_user_agents(user_id: int) -> Optional[list]:
    """Get cached user agents list."""
    return cache.get(f"user:{user_id}:agents")


# LRU Cache for expensive computations
@lru_cache(maxsize=100)
def cached_domain_analysis(prompt_hash: str) -> dict:
    """
    LRU cache for domain analysis results.
    Use hash of prompt as key to avoid storing full prompts.
    """
    # This is a placeholder - actual analysis happens in prompt_analyzer
    return {}
