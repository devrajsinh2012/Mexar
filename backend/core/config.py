
import os
from dotenv import load_dotenv

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
    
    # Storage
    STORAGE_PATH = os.getenv("STORAGE_PATH", "./data/storage")
    
    # Caching (In-memory for dev, Redis for prod)
    REDIS_URL = os.getenv("REDIS_URL")  # Optional
    
settings = Config()
