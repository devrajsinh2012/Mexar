"""
MEXAR Core Engine - FastAPI Backend Application
Main entry point for the MEXAR Phase 2 API.

This is a clean, minimal main.py that only includes routers.
All endpoints are handled by the api/ modules.
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure data directories exist
DATA_DIRS = [
    Path("data/storage"),
    Path("data/temp"),
]
for dir_path in DATA_DIRS:
    dir_path.mkdir(parents=True, exist_ok=True)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - database initialization."""
    logger.info("MEXAR Core Engine starting up...")
    
    # Initialize database tables
    try:
        from core.database import engine, Base
        from models.user import User
        from models.agent import Agent, CompilationJob
        from models.conversation import Conversation, Message
        from models.chunk import DocumentChunk
        from sqlalchemy import text

        # Enable vector extension
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.warning(f"Database initialization: {e}")
    
    yield
    logger.info("MEXAR Core Engine shutting down...")


# Create FastAPI app
app = FastAPI(
    title="MEXAR Core Engine",
    description="Multimodal Explainable AI Reasoning Assistant - Phase 2",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
# Configure CORS
# CRITICAL: Configure CORS for Vercel frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

allow_origins = [
    "*", 
    FRONTEND_URL, 
    "https://*.vercel.app", 
    "http://localhost:3000",
    "http://localhost:3001"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include Phase 2 routers
from api import auth, agents, chat, compile, websocket, admin, prompts, diagnostics

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(compile.router)
app.include_router(websocket.router)
app.include_router(admin.router)
app.include_router(prompts.router)
app.include_router(diagnostics.router)


# ===== CORE UTILITY ENDPOINTS =====

@app.get("/")
async def root():
    """Root endpoint - serves landing page."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html")
    else:
        # Fallback to JSON if HTML not found
        return {
            "name": "MEXAR Core Engine",
            "version": "2.0.0",
            "status": "operational",
            "docs": "/docs"
        }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "groq_configured": bool(os.getenv("GROQ_API_KEY"))
    }





# ===== ERROR HANDLERS =====

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# ===== MAIN ENTRY POINT =====

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
