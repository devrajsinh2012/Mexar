
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
load_dotenv()

class Config:
    # Database (Default to SQLite for dev)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mexar.db")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
    
    # AI Services
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    LLM_BACKBONE = os.getenv("LLM_BACKBONE", "llama3")  # Options: llama3, gpt-oss-120b
    GROQ_MODEL = os.getenv("GROQ_MODEL", os.getenv("LLM_MODEL", "llama-3.1-8b-instant"))
    
    # Storage
    STORAGE_PATH = os.getenv("STORAGE_PATH", "./data/storage")
    
    # Caching (In-memory for dev, Redis for prod)
    REDIS_URL = os.getenv("REDIS_URL")  # Optional
    
settings = Config()
