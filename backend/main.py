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

        # Enable vector extension only for postgres
        if "sqlite" not in str(engine.url):
            try:
                with engine.connect() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    conn.commit()
            except Exception as vector_err:
                logger.warning(f"Vector extension check skipped: {vector_err}")

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


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).parent / "static"

# Mount static subfolder for compiled CSS/JS assets if present
if (STATIC_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR / "static")), name="static_assets")


# ===== CORE UTILITY ENDPOINTS =====

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "groq_configured": bool(os.getenv("GROQ_API_KEY"))
    }


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve React SPA frontend for root and all client-side routes."""
    # Do not intercept API, docs, or WebSocket endpoints
    if full_path.startswith("api/") or full_path.startswith("ws/") or full_path in ["docs", "redoc", "openapi.json"]:
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    # Direct static file request (e.g. favicon.ico, asset-manifest.json)
    if full_path:
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

    # Fallback to index.html for SPA routing
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")

    return JSONResponse(
        status_code=404,
        content={
            "name": "MEXAR Core Engine",
            "version": "2.0.0",
            "status": "operational",
            "docs": "/docs"
        }
    )






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
