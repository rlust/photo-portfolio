"""Database configuration and utilities."""
import os
import logging
from typing import Generator, Optional, Dict, Any
from contextlib import contextmanager
from functools import wraps

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy_utils import database_exists, create_database

from .config import settings, logger, Base

# Create database engine with connection pooling
engine = None
SessionLocal = None

def init_engine():
    """Initialize the database engine with proper configuration."""
    global engine, SessionLocal
    
    if engine is not None:
        return engine, SessionLocal
        
    logger.info(f"Initializing database engine with URI: {settings.DATABASE_URI}")
    
    # Configure connection pool settings
    pool_config = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,  # Recycle connections after 1 hour
        'pool_size': 5,
        'max_overflow': 10,
        'echo': settings.DEBUG,
        'connect_args': {}
    }
    
    # Add SSL configuration if not running in Cloud Run
    if not os.getenv('K_SERVICE'):
        pool_config['connect_args'] = {
            'sslmode': 'require',
            'options': f'-c timezone=utc',
        }
    
    try:
        # Diagnostic: Print the actual DATABASE_URI used for engine creation
        import sys
        print(f"[DATABASE_URI_USED_FOR_ENGINE_CREATION] {settings.DATABASE_URI}", file=sys.stderr)
        logger.info(f"[DATABASE_URI_USED_FOR_ENGINE_CREATION] {settings.DATABASE_URI}")
        engine = create_engine(settings.DATABASE_URI, **pool_config)
        logger.info("Database engine created successfully")
        
        # Configure session factory with error handling
        try:
            SessionLocal = scoped_session(
                sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=engine,
                    expire_on_commit=False
                )
            )
            logger.info("Database session factory configured")
        except Exception as e:
            logger.error(f"Failed to configure database session factory: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise
        
    # Configure connection pooling with ping for connection validation
    @event.listens_for(engine, 'engine_connect')
    def ping_connection(connection, branch):
        """Ping the database connection before using it to ensure it's still valid.
        
        This works with SQLAlchemy 1.4+ which uses the connection object directly.
        """
        if branch:
            # 'branch' refers to a sub-transaction; we don't want to run a ping on these
            return
        
        # Skip ping if we're in the middle of a transaction
        if connection.in_transaction():
            return
            
        # Save the current transaction state
        save_should_close_with_result = connection.should_close_with_result
        connection.should_close_with_result = False
        
        try:
            # Use the connection's execute method to run a simple query
            connection.scalar(text('SELECT 1'))
            logger.debug("Database connection ping successful")
        except Exception as e:
            # If the connection is not valid, log the error and raise an exception
            # to force a new connection
            logger.error("Database connection check failed: %s", str(e))
            # Disconnect handling - this will force a reconnection next time
            try:
                connection.invalidate()
                logger.info("Invalidated database connection")
            except Exception as invalidate_error:
                logger.error("Failed to invalidate connection: %s", str(invalidate_error))
            raise OperationalError("Database connection is not valid") from e
        finally:
            # Restore the connection's original state
            connection.should_close_with_result = save_should_close_with_result
    
    logger.info("Database engine initialization complete")
    return engine, SessionLocal

# Initialize the engine and session factory
engine, SessionLocal = init_engine()

def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function creates all database tables defined in the SQLAlchemy models.
    It's safe to call this function multiple times as it won't recreate existing tables.
    """
    try:
        # Import all models here to ensure they are registered with SQLAlchemy
        from . import models  # noqa: F401
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def reset_db() -> bool:
    """
    Reset the database by dropping all tables and recreating them.
    
    This function is destructive and should only be used in development and testing.
    It will drop all tables and then recreate them from the current models.
    
    Returns:
        bool: True if the reset was successful, False otherwise
    """
    try:
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Dropped all tables.")
        
        logger.info("Recreating all tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Recreated all tables.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

def check_db_connection() -> bool:
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if the connection is successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that yields a database session.
    
    This is used as a FastAPI dependency to get a database session.
    The session is automatically closed when the request is complete.
    FastAPI will handle the dependency life cycle using the Generator pattern.
    
    Yields:
        Session: A SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Database error: %s", str(e))
        raise
    finally:
        db.close()

def execute_sql_file(file_path: str) -> None:
    """
    Execute SQL commands from a file.
    
    Args:
        file_path (str): Path to the SQL file to execute
    """
    if not os.path.exists(file_path):
        logger.error(f"SQL file not found: {file_path}")
        return
    
    with open(file_path, 'r') as f:
        sql_commands = f.read()
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text(sql_commands))
    
    logger.info(f"Executed SQL file: {file_path}")

# The event listener is now registered in the init_engine function

def drop_and_recreate_db() -> bool:
    """
    Drop and recreate the database.
    
    This function is destructive and should only be used in development and testing.
    It will drop the database and then recreate it.
    
    Returns:
        bool: True if the reset was successful, False otherwise
    """
    db_uri = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/postgres"
    
    try:
        temp_engine = create_engine(db_uri, isolation_level='AUTOCOMMIT')
        
        with temp_engine.connect() as conn:
            # Disconnect all other connections
            conn.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{DB_CONFIG['name']}'
                AND pid <> pg_backend_pid();
            """)
            
            # Drop and recreate the database
            conn.execute(f"DROP DATABASE IF EXISTS {DB_CONFIG['name']} WITH (FORCE)")
            print(f"Dropped database: {DB_CONFIG['name']}")
            
            conn.execute(f"CREATE DATABASE {DB_CONFIG['name']}")
            print(f"Created database: {DB_CONFIG['name']}")
        
        # Create all tables
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("Database reset successfully!")
        return True
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        raise
