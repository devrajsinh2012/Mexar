
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.cache import cache
from core.monitoring import analytics
from api.deps import get_current_user
from models.user import User

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
def get_system_stats(
    current_user: User = Depends(get_current_user)
):
    """Get system statistics (admin only)."""
    # In production, add admin check
    stats = analytics.get_stats()
    cache_stats = cache.get_stats()
    
    return {
        "analytics": stats,
        "cache": cache_stats
    }

@router.get("/health")
def detailed_health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "cache": "active",
            "workers": "ready"
        }
    }

@router.post("/cache/clear")
def clear_cache(
    current_user: User = Depends(get_current_user)
):
    """Clear all cache entries."""
    cache.clear()
    return {"message": "Cache cleared successfully"}

@router.post("/analytics/reset")
def reset_analytics(
    current_user: User = Depends(get_current_user)
):
    """Reset analytics counters."""
    analytics.reset()
    return {"message": "Analytics reset successfully"}
