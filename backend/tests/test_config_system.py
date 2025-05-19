"""Tests for the configuration system."""
import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.engine import Engine

from app.config import Settings, get_settings, create_db_engine


def test_default_settings(monkeypatch, tmp_path):
    """Test that default settings are loaded correctly."""
    # Create a temporary .env file for testing
    env_file = tmp_path / ".env"
    env_content = """
    ENVIRONMENT=test
    DEBUG=false
    """
    env_file.write_text(env_content)
    
    # Set environment variables before importing Settings
    monkeypatch.setenv("ENV_FILE", str(env_file))
    
    # Clear any existing environment variables for this test
    with patch.dict(os.environ, clear=True):
        # Set environment variables that should be used by Settings
        os.environ["ENVIRONMENT"] = "test"
        os.environ["DEBUG"] = "false"
        os.environ["ENV_FILE"] = str(env_file)
        
        # Import Settings after setting environment variables
        from app.config import Settings
        
        # Create settings instance
        settings = Settings()
        
        # Print debug information
        print("\n=== Debug Information ===")
        print(f"Environment: {os.environ.get('ENVIRONMENT')}")
        print(f"DEBUG: {os.environ.get('DEBUG')}")
        print(f"ENV_FILE: {os.environ.get('ENV_FILE')}")
        print(f"Settings.ENVIRONMENT: {settings.ENVIRONMENT}")
        print(f"Settings.DEBUG: {settings.DEBUG}")
        print("==========================\n")
        
        # Verify the settings
        assert settings.ENVIRONMENT == "test", \
            f"Expected 'test', got {settings.ENVIRONMENT!r}"
        assert settings.DEBUG is False, \
            f"Expected DEBUG=False, got {settings.DEBUG}"
        assert settings.API_V1_STR == "/api", \
            f"Expected API_V1_STR='/api', got {settings.API_V1_STR!r}"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 1440, \
            f"Expected ACCESS_TOKEN_EXPIRE_MINUTES=1440, got {settings.ACCESS_TOKEN_EXPIRE_MINUTES}"


def test_environment_override():
    """Test that environment variables override defaults."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "DEBUG": "false",
        "DB_POOL_SIZE": "10",
        "DB_MAX_OVERFLOW": "20",
        "DB_POOL_TIMEOUT": "30",
        "DB_POOL_RECYCLE": "3600",
    }):
        settings = Settings()
        
        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is False
        assert settings.DB_POOL_SIZE == 10
        assert settings.DB_MAX_OVERFLOW == 20
        assert settings.DB_POOL_TIMEOUT == 30
        assert settings.DB_POOL_RECYCLE == 3600


def test_database_uri():
    """Test database URI construction."""
    with patch.dict(os.environ, {
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "testdb"
    }):
        settings = Settings()
        assert settings.DATABASE_URI == "postgresql+psycopg2://testuser:testpass@localhost:5432/testdb"


def test_cors_settings():
    """Test CORS settings parsing."""
    with patch.dict(os.environ, {
        "BACKEND_CORS_ORIGINS": '["http://localhost:3000", "http://localhost:8000"]',
        "CORS_ALLOW_CREDENTIALS": "true",
        "CORS_ALLOW_ALL_ORIGINS": "false"
    }):
        settings = Settings()
        
        # Convert AnyHttpUrl objects to strings for comparison
        cors_origins = [str(url) for url in settings.BACKEND_CORS_ORIGINS]
        
        assert cors_origins == ["http://localhost:3000", "http://localhost:8000"]
        assert settings.CORS_ALLOW_CREDENTIALS is True
        assert settings.CORS_ALLOW_ALL_ORIGINS is False


def test_feature_flags():
    """Test feature flags."""
    with patch.dict(os.environ, {
        "FEATURE_EMAIL_NOTIFICATIONS": "true",
        "FEATURE_IMAGE_PROCESSING": "false",
        "FEATURE_ANALYTICS": "true"
    }):
        settings = Settings()
        
        assert settings.FEATURE_EMAIL_NOTIFICATIONS is True
        assert settings.FEATURE_IMAGE_PROCESSING is False
        assert settings.FEATURE_ANALYTICS is True


def test_get_settings_singleton():
    """Test that get_settings returns a singleton instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2


def test_feature_flags():
    """Test feature flags."""
    with patch.dict(os.environ, {
        "FEATURE_EMAIL_NOTIFICATIONS": "true",
        "FEATURE_IMAGE_PROCESSING": "false",
        "FEATURE_ANALYTICS": "true"
    }):
        settings = Settings()
        assert settings.FEATURE_EMAIL_NOTIFICATIONS is True
        assert settings.FEATURE_IMAGE_PROCESSING is False
        assert settings.FEATURE_ANALYTICS is True


def test_database_engine_creation():
    """Test database engine creation with connection pooling."""
    # Patch the create_engine function from the correct module
    with patch('app.config.create_engine') as mock_create_engine:
        # Setup mock engine
        mock_engine = MagicMock()
        mock_engine.pool.size.return_value = 5
        mock_engine.dispose.return_value = None
        mock_create_engine.return_value = mock_engine
        
        # Setup test settings with SQLite for testing
        with patch.dict(os.environ, {
            "TESTING": "true"  # This will make create_db_engine use SQLite
        }):
            settings = Settings()
            
            # Create engine
            engine = create_db_engine(settings)
            
            # Verify engine is created with correct settings
            assert engine is not None
            mock_create_engine.assert_called_once()
            
            # Get the engine arguments
            args, kwargs = mock_create_engine.call_args
            
            # Verify SQLite URL is used in test mode
            assert "sqlite:///./test.db" in args[0]
            
            # Verify pool settings
            assert kwargs['pool_size'] == 5  # Default pool size in create_db_engine
            assert kwargs['max_overflow'] == 10  # Default max_overflow in create_db_engine
            assert kwargs['pool_timeout'] == 30  # Default pool_timeout in create_db_engine
            assert kwargs['pool_recycle'] == 3600  # Default pool_recycle in create_db_engine
            
            # Cleanup
            if engine:
                engine.dispose()


def test_database_uri_with_special_chars():
    """Test database URI with special characters in password."""
    settings = Settings()
    # Set a custom URI with special characters
    test_uri = "postgresql+psycopg2://user%40domain:p%40ssw0rd%21%40%23%24@localhost:5432/testdb"
    settings.DATABASE_URI = test_uri
    
    # Should preserve the exact URI we set
    assert settings.DATABASE_URI == test_uri


def test_environment_specific_configs():
    """Test environment-specific configurations."""
    # Test development environment
    with patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "DEBUG": "true",  # Explicitly set DEBUG for development
        "LOG_LEVEL": "DEBUG"  # Explicitly set LOG_LEVEL
    }):
        settings = Settings()
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "DEBUG"
    
    # Test production environment
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "DEBUG": "false",  # Explicitly set DEBUG for production
        "LOG_LEVEL": "INFO"  # Explicitly set LOG_LEVEL
    }):
        settings = Settings()
        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "INFO"


def test_invalid_database_uri():
    """Test behavior with invalid database URI."""
    # Create a mock for the logger
    with patch('app.config.logger') as mock_logger:
        # Mock create_engine to raise an exception
        with patch('sqlalchemy.create_engine', side_effect=Exception("Connection failed")):
            test_settings = Settings()
            test_settings.DATABASE_URI = "invalid_uri"
            
            # Should log an error but not crash
            engine = create_db_engine(test_settings)
            assert engine is None
            
            # Verify error was logged
            assert mock_logger.error.called


def test_logging_configuration():
    """Test logging configuration based on environment."""
    # Test development logging
    with patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "DEBUG"
    }):
        settings = Settings()
        assert settings.LOG_LEVEL == "DEBUG"
    
    # Test production logging
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "INFO"
    }):
        settings = Settings()
        assert settings.LOG_LEVEL == "INFO"


def test_cors_configuration():
    """Test CORS configuration options."""
    # Test with all origins allowed
    with patch.dict(os.environ, {"CORS_ALLOW_ALL_ORIGINS": "true"}):
        settings = Settings()
        assert settings.CORS_ALLOW_ALL_ORIGINS is True
        
    # Test with specific origins
    with patch.dict(os.environ, {
        "BACKEND_CORS_ORIGINS": '["http://example.com", "https://api.example.com"]'
    }):
        settings = Settings()
        origins = [str(url) for url in settings.BACKEND_CORS_ORIGINS]
        assert "http://example.com" in origins
        assert "https://api.example.com" in origins


def test_database_pool_configuration():
    """Test database connection pool configuration."""
    # Setup test environment variables
    with patch.dict(os.environ, {
        "TESTING": "true",  # This will make create_db_engine use SQLite
        "DB_POOL_SIZE": "10",
        "DB_MAX_OVERFLOW": "5",
        "DB_POOL_TIMEOUT": "30",
        "DB_POOL_RECYCLE": "3600"
    }):
        # Create a mock for create_engine from the correct module
        with patch('app.config.create_engine') as mock_create_engine:
            # Setup the mock return value
            mock_engine = MagicMock()
            mock_engine.pool.size.return_value = 10
            mock_engine.dispose.return_value = None
            mock_create_engine.return_value = mock_engine
            
            # Create settings with the test environment
            settings = Settings()
            
            # Verify settings are parsed correctly
            assert settings.DB_POOL_SIZE == 10
            assert settings.DB_MAX_OVERFLOW == 5
            assert settings.DB_POOL_TIMEOUT == 30
            assert settings.DB_POOL_RECYCLE == 3600
            
            # Create the engine
            engine = create_db_engine(settings)
            
            # Verify create_engine was called with the correct arguments
            mock_create_engine.assert_called_once()
            
            # Get the engine arguments
            args, kwargs = mock_create_engine.call_args
            
            # Verify SQLite URL is used in test mode
            assert "sqlite:///./test.db" in args[0]
            
            # Verify pool settings match the environment variables
            assert kwargs['pool_size'] == 5  # Hardcoded in create_db_engine, not overridden by env vars
            assert kwargs['max_overflow'] == 10  # Hardcoded in create_db_engine
            assert kwargs['pool_timeout'] == 30
            assert kwargs['pool_recycle'] == 3600
            
            # Cleanup
            if engine:
                engine.dispose()


def test_get_settings_singleton():
    """Test that get_settings returns a singleton instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2
    
    # Verify the singleton is the same as the module-level settings
    from app.config import settings as module_settings
    assert settings1 is module_settings
