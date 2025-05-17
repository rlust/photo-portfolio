import os
import logging
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, text, event, Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker, scoped_session, Session, declarative_base
from sqlalchemy_utils import database_exists, create_database

from .config import Base, engine, SessionLocal, settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that yields a database session.
    
    This is used as a FastAPI dependency to get a database session.
    The session is automatically closed when the request is complete.
    
    Yields:
        Session: A SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
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

# Add event listeners for connection management
@event.listens_for(engine, 'engine_connect')
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    """
    Ping the database connection before using it to ensure it's still valid.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except:
        # If the connection is not valid, raise an error to force a new connection
        raise OperationalError("Database connection is not valid")
    finally:
        cursor.close()

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
