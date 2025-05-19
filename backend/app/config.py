import os
import sys
print('[CONFIG_PY_EARLY_START]', file=sys.stderr)
for k, v in sorted(os.environ.items()):
    print(f'[CONFIG_PY_EARLY_ENV] {k}={v}', file=sys.stderr)
import logging
from pathlib import Path
from typing import Optional, List, Any, Dict, Union, Set

from pydantic import PostgresDsn, validator, Field, AnyHttpUrl, HttpUrl
import os
print("[DEBUG] ENVIRONMENT VARIABLES AT PROCESS START:")
for k, v in sorted(os.environ.items()):
    print(f"    {k}={v}")
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine

# Load environment variables from .env file if it exists
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Add file handler if LOG_FILE is set
if log_file := os.getenv("LOG_FILE"):
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,
        env_nested_delimiter='__',
    )
    
    # Make DATABASE_URI settable
    _database_uri: Optional[str] = None
    
    # ===================================
    # Application Settings
    # ===================================
    APP_NAME: str = Field(default="Photo Portfolio API")
    APP_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    
    # ===================================
    # API Settings
    # ===================================
    API_V1_STR: str = Field(default="/api")
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)  # 24 hours
    
    # ===================================
    # CORS Settings
    # ===================================
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = os.getenv(
        "BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(",") if os.getenv("BACKEND_CORS_ORIGINS") else []
    
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in ("true", "1", "t")
    CORS_ALLOW_ALL_ORIGINS: bool = os.getenv("CORS_ALLOW_ALL_ORIGINS", "false").lower() in ("true", "1", "t")
    
    # ===================================
    # Database Settings
    # ===================================
    DB_USER: str = os.getenv("DB_USER", "rlust")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "photoportfolio")
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "public")
    
    # Construct the database URL
    @property
    def DATABASE_URI(self) -> str:
        """Construct the database connection string."""
        if self._database_uri:
            return self._database_uri
            
        # Handle special characters in password
        from urllib.parse import quote_plus
        safe_password = quote_plus(self.DB_PASSWORD)
        
        # If running with Cloud SQL connection name (Cloud Run or similar)
        if self.CLOUD_SQL_CONNECTION_NAME:
            logger.info(f"Using Cloud SQL connection: {self.CLOUD_SQL_CONNECTION_NAME}")
            return f"postgresql+psycopg2://{self.DB_USER}:{safe_password}@/{self.DB_NAME}?host=/cloudsql/{self.CLOUD_SQL_CONNECTION_NAME}"
        
        # Local development with direct connection
        return f"postgresql+psycopg2://{self.DB_USER}:{safe_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
    @DATABASE_URI.setter
    def DATABASE_URI(self, value: str) -> None:
        """Set a custom database URI."""
        self._database_uri = value
        
    # Add missing attributes
    LOG_LEVEL: str = Field(default="INFO")
    FEATURE_EMAIL_NOTIFICATIONS: bool = Field(default=False)
    FEATURE_IMAGE_PROCESSING: bool = Field(default=True)
    FEATURE_ANALYTICS: bool = Field(default=False)
    SENTRY_DSN: Optional[str] = Field(default=None)
    GOOGLE_ANALYTICS_ID: Optional[str] = Field(default=None)

    # Connection pool settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # seconds
    
    # Google Cloud SQL connection name (format: project:region:instance)
    CLOUD_SQL_CONNECTION_NAME: Optional[str] = os.getenv("CLOUD_SQL_CONNECTION_NAME")
    
    # ===================================
    # Google Cloud Storage Configuration
    # ===================================
    GCS_BUCKET: Optional[str] = os.getenv("GCS_BUCKET")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GOOGLE_CLOUD_PROJECT: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    # ===================================
    # File Upload Settings
    # ===================================
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))  # 10MB default
    ALLOWED_EXTENSIONS: Set[str] = set(
        ext.strip().lower() 
        for ext in os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif,webp").split(",")
    )
    
    # ===================================
    # Security Settings
    # ===================================
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "100"))  # requests per minute per IP
    
    # ===================================
    # Feature Flags
    # ===================================
    FEATURE_EMAIL_NOTIFICATIONS: bool = os.getenv("FEATURE_EMAIL_NOTIFICATIONS", "false").lower() in ("true", "1", "t")
    FEATURE_IMAGE_PROCESSING: bool = os.getenv("FEATURE_IMAGE_PROCESSING", "true").lower() in ("true", "1", "t")
    FEATURE_ANALYTICS: bool = os.getenv("FEATURE_ANALYTICS", "false").lower() in ("true", "1", "t")
    
    # ===================================
    # Monitoring and Logging
    # ===================================
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    GOOGLE_ANALYTICS_ID: Optional[str] = os.getenv("GOOGLE_ANALYTICS_ID")
    
    # ===================================
    # Model Configuration
    # ===================================
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        validate_assignment=True,
        env_nested_delimiter='__'
    )
    
    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "gif", "webp"}
    
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")  # env_file removed for production safety

# Initialize settings with crash diagnostics
try:
    settings = Settings()

    # Debug logging for DB connection environment
    logger.info(f"CLOUD_SQL_CONNECTION_NAME: {settings.CLOUD_SQL_CONNECTION_NAME}")
    logger.info(f"DB_HOST: {settings.DB_HOST}")
    logger.info(f"DB_PORT: {settings.DB_PORT}")
    logger.info(f"DATABASE_URI: {settings.DATABASE_URI}")

    # Fallback print for Cloud Run log visibility
    print(f"CLOUD_SQL_CONNECTION_NAME: {settings.CLOUD_SQL_CONNECTION_NAME}")
    print(f"DB_HOST: {settings.DB_HOST}")
    print(f"DB_PORT: {settings.DB_PORT}")
    print(f"DATABASE_URI: {settings.DATABASE_URI}")
except Exception as e:
    print("FATAL: Exception during settings initialization or logging:")
    import traceback
    traceback.print_exc()
    raise

def get_settings() -> Settings:
    """
    Get the application settings.
    
    Returns:
        Settings: The application settings instance
    """
    return settings

# Configure SQLAlchemy engine with connection pooling and ping handler
def create_db_engine(settings: Settings) -> Optional[Engine]:
    """
    Create and configure the SQLAlchemy engine with connection pooling.
    
    Args:
        settings: Application settings instance
        
    Returns:
        Configured SQLAlchemy engine or None if configuration is invalid
    """
    try:
        # Get the database URI
        database_uri = settings.DATABASE_URI
        
        # For testing, use SQLite
        if os.getenv("TESTING", "false").lower() == "true":
            database_uri = "sqlite:///./test.db"
            logger.info("Using SQLite database for testing")
        
        # Configure connection pooling
        engine = create_engine(
            database_uri,
            poolclass=QueuePool,
            pool_size=5,  # Number of connections to keep open
            max_overflow=10,  # Number of connections to allow in overflow
            pool_timeout=30,  # Seconds to wait before giving up on getting a connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Enable connection health checks
            echo=settings.DEBUG,  # Enable SQL query logging in debug mode
            connect_args={
                "connect_timeout": 10,  # Connection timeout in seconds
                "keepalives": 1,  # Enable TCP keepalive
                "keepalives_idle": 30,  # Time before sending keepalive packets
                "keepalives_interval": 10,  # Interval between keepalive packets
                "keepalives_count": 5,  # Number of keepalive packets before dropping connection
                "options": f"-c search_path={settings.DB_SCHEMA}",  # Set the schema
            } if "postgresql" in database_uri else {"check_same_thread": False},  # SQLite specific
        )
        
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            
        logger.info(f"Successfully connected to database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        return engine
        
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        if settings.ENVIRONMENT == "development" or settings.ENVIRONMENT == "test":
            logger.warning(f"Running in {settings.ENVIRONMENT} mode - some features may not work without a database")
            return None
        if settings.ENVIRONMENT == "production":
            raise
        return None

# Create the database engine and session factory
engine = create_db_engine(settings)

if engine is not None:
    # Create session factory
    SessionLocal = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False
        )
    )
    
    logger.info("Database engine and session factory initialized successfully")
else:
    logger.warning("Database engine not initialized. Some features may not work.")
    SessionLocal = None

# Base class for models
Base = declarative_base()

def get_db() -> Session:
    """
    Dependency to get DB session.
    
    Yields:
        SQLAlchemy database session
        
    Raises:
        RuntimeError: If database is not available
    """
    if SessionLocal is None:
        raise RuntimeError("Database is not available. Check your database configuration.")
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()

# Create necessary directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
logger.info(f"Ensured upload directory exists: {settings.UPLOAD_DIR}")

