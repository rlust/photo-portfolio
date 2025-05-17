import os
import logging
from typing import Optional, List, Any, Dict
from pydantic import PostgresDsn, validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Photo Portfolio API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # API settings
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Database settings
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "photo_portfolio")
    DATABASE_URI: Optional[PostgresDsn] = None
    
    @validator("DATABASE_URI", pre=True)
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if isinstance(v, str):
            return v
            
        # Try to get database credentials from Secret Manager if enabled
        if values.get('USE_SECRET_MANAGER', False) and values.get('SECRET_MANAGER_PROJECT_ID'):
            try:
                from app.utils.secrets import get_database_credentials
                db_creds = get_database_credentials()
                
                # Update values with credentials from Secret Manager
                values['DB_USER'] = db_creds.get('DB_USER', values.get('DB_USER', ''))
                values['DB_PASSWORD'] = db_creds.get('DB_PASSWORD', values.get('DB_PASSWORD', ''))
                values['DB_HOST'] = db_creds.get('DB_HOST', values.get('DB_HOST', 'localhost'))
                values['DB_PORT'] = db_creds.get('DB_PORT', values.get('DB_PORT', '5432'))
                values['DB_NAME'] = db_creds.get('DB_NAME', values.get('DB_NAME', 'photo_portfolio'))
                
                logger.info("Successfully loaded database credentials from Secret Manager")
            except Exception as e:
                logger.warning(f"Failed to load database credentials from Secret Manager: {str(e)}")
                logger.warning("Falling back to environment variables")
        
        from urllib.parse import quote_plus
        user = values.get('DB_USER')
        password = values.get('DB_PASSWORD', '')
        host = values.get('DB_HOST', 'localhost')
        port = values.get('DB_PORT', '5432')
        db_name = values.get('DB_NAME', 'photo_portfolio')
        
        if not all([user, password, host, db_name]):
            raise ValueError("Missing required database connection parameters")
            
        # Properly encode the password
        encoded_password = quote_plus(password)
        return f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{db_name}"
    
    # Google Cloud Storage settings
    GCS_BUCKET: Optional[str] = os.getenv("GCS_BUCKET")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "gif", "webp"}
    
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

# Initialize settings
settings = Settings()

# Ensure DATABASE_URI is a string
if isinstance(settings.DATABASE_URI, str):
    database_uri = settings.DATABASE_URI
else:
    database_uri = str(settings.DATABASE_URI) if settings.DATABASE_URI else None

if not database_uri:
    raise ValueError("DATABASE_URI is not configured")

# Create database engine with connection pooling
engine = create_engine(
    database_uri,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False
    )
)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create upload directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
