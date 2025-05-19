"""Pytest configuration and fixtures for testing the Photo Portfolio backend."""
import os
import sys
from pathlib import Path
from typing import Generator, Any, Callable, Iterator

# Set testing environment variables before any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key"

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after setting environment variables
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config import Base, get_db, Settings, engine as main_engine, SessionLocal
from app.models.user import User, UserCreate
from app.models.photo import Photo
from app.security import get_password_hash, create_access_token

# Create a test settings instance
test_settings = Settings()

# Test database URL - using SQLite in-memory for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create test engine and session
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Use a static pool for SQLite in-memory
    echo=True  # Enable SQL query logging for tests
)

# Create a test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database
def override_get_db() -> Generator[Session, None, None]:
    """Override the get_db dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the get_db dependency in the app
app.dependency_overrides[get_db] = override_get_db

# Create all tables before tests and drop them after
def create_test_tables() -> None:
    """Create all database tables for testing."""
    Base.metadata.create_all(bind=engine)

def drop_test_tables() -> None:
    """Drop all database tables after testing."""
    Base.metadata.drop_all(bind=engine)

# Set up the test database
@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Iterator[None]:
    """Set up the test database before running tests."""
    # Create tables
    create_test_tables()
    
    # Yield control to tests
    yield
    
    # Clean up
    drop_test_tables()

# Fixtures
@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Begin a nested transaction (using SAVEPOINT)
    nested = connection.begin_nested()

    # If the application code calls session.commit, it will end the nested
    # transaction. Need to start a new one when that happens.
    @event.listens_for(session, 'after_transaction_end')
    def end_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    # Clean up
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    # Create test client with the app
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    from app.security import get_password_hash
    
    user_data = {
        "email": "test@example.com",
        "password": "testpassword",
        "full_name": "Test User"
    }
    
    user = User(
        email=user_data["email"],
        hashed_password=get_password_hash(user_data["password"]),
        full_name=user_data["full_name"],
        is_active=True,
        is_superuser=False
    )
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_superuser(db_session: Session) -> User:
    """Create a test superuser."""
    from app.security import get_password_hash
    
    user_data = {
        "email": "admin@example.com",
        "password": "adminpassword",
        "full_name": "Admin User"
    }
    
    user = User(
        email=user_data["email"],
        hashed_password=get_password_hash(user_data["password"]),
        full_name=user_data["full_name"],
        is_active=True,
        is_superuser=True
    )
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_photo(db_session: Session, test_user: User) -> Photo:
    """Create a test photo."""
    from datetime import datetime, timezone
    
    photo_data = {
        "title": "Test Photo",
        "description": "A test photo",
        "url": "http://example.com/test.jpg",
        "mimetype": "image/jpeg",
        "file_size": 1024,
        "width": 800,
        "height": 600,
        "is_public": True,
        "location_tag": "Test Location"
    }
    
    photo = Photo(
        **photo_data,
        owner_id=test_user.id,
        uploaded_at=datetime.now(timezone.utc)
    )
    
    db_session.add(photo)
    db_session.commit()
    db_session.refresh(photo)
    return photo

@pytest.fixture
def test_token(test_user: User) -> str:
    """Generate a test JWT token."""
    from datetime import timedelta
    from app.security import create_access_token

    access_token = create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email, "is_superuser": test_user.is_superuser},
        expires_delta=timedelta(minutes=15)
    )
    return access_token

@pytest.fixture
def authorized_client(test_client: TestClient, test_token: str) -> TestClient:
    """Return a test client with authentication headers."""
    test_client.headers.update({
        "Authorization": f"Bearer {test_token}"
    })
    return test_client

@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "True")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    monkeypatch.setenv("UPLOAD_DIR", "test_uploads")
    
    # Ensure we're using the test database
    monkeypatch.setattr("app.config.engine", engine)
    monkeypatch.setattr("app.config.SessionLocal", TestingSessionLocal)
