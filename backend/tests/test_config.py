"""Test configuration for the Photo Portfolio backend."""
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings, Base, get_db
from app.main import app

# Test database URL - using SQLite for simplicity
TEST_DATABASE_URL = "sqlite:///./test.db"


def get_test_settings() -> Settings:
    """Get test settings with SQLite database."""
    return Settings(
        ENVIRONMENT="test",
        DEBUG=True,
        DATABASE_URI=TEST_DATABASE_URL,
        DB_POOL_SIZE=1,
        DB_MAX_OVERFLOW=0,
        DB_POOL_TIMEOUT=30,
        DB_POOL_RECYCLE=3600,
        UPLOAD_DIR=str(Path(__file__).parent / "test_uploads"),
        MAX_UPLOAD_SIZE=5 * 1024 * 1024,  # 5MB
        ALLOWED_EXTENSIONS={"jpg", "jpeg", "png", "gif"},
        SECRET_KEY="test-secret-key",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        CORS_ALLOW_ORIGINS=["*"],
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ALLOW_METHODS=["*"],
        CORS_ALLOW_HEADERS=["*"],
    )


@pytest.fixture(scope="session")
def test_settings():
    """Test settings fixture."""
    return get_test_settings()


@pytest.fixture(scope="session")
def engine(test_settings):
    """Create a test database engine."""
    # Create test upload directory
    os.makedirs(test_settings.UPLOAD_DIR, exist_ok=True)
    
    # Create test database
    engine = create_engine(
        test_settings.DATABASE_URI,
        connect_args={"check_same_thread": False}  # Required for SQLite
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up
    Base.metadata.drop_all(bind=engine)
    
    # Remove test database file if using SQLite
    if test_settings.DATABASE_URI.startswith("sqlite"):
        db_path = test_settings.DATABASE_URI.replace("sqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)
    
    # Remove test upload directory
    if os.path.exists(test_settings.UPLOAD_DIR):
        for file in os.listdir(test_settings.UPLOAD_DIR):
            os.remove(os.path.join(test_settings.UPLOAD_DIR, file))
        os.rmdir(test_settings.UPLOAD_DIR)


@pytest.fixture
def db_session(engine):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    
    # Create a session with the connection
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()
    
    # Begin a nested transaction
    session.begin_nested()
    
    # Set up the savepoint
    @event.listens_for(session, 'after_transaction_end')
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()
    
    yield session
    
    # Clean up
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create a test client with a database session."""
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Don't close the session here, it's managed by the fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    with app.test_client() as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()
