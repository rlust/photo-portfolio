import os
import sys
import logging
from sqlalchemy import create_engine, text
from google.cloud.sql.connector import Connector, IPTypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a database connection using SQLAlchemy with direct connection to Cloud SQL."""
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')
    db_host = os.environ.get('DB_HOST', '34.28.227.126')  # Public IP of the Cloud SQL instance
    db_port = os.environ.get('DB_PORT', '5432')
    
    if not all([db_user, db_password, db_name]):
        raise ValueError("Missing required database environment variables")
    
    logger.info(f"Connecting to database: {db_name} on {db_host}:{db_port}")
    
    try:
        # Create connection string for SQLAlchemy with psycopg2
        db_uri = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        logger.info(f"Database URI: postgresql+psycopg2://{db_user}:*****@{db_host}:{db_port}/{db_name}")
        
        # Create SQLAlchemy engine with psycopg2
        engine = create_engine(
            db_uri,
            pool_size=1,
            max_overflow=1,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={
                'connect_timeout': 10,
                'sslmode': 'disable'  # Disable SSL for testing
            }
        )
        
        return engine
        
    except Exception as e:
        logger.error(f"Failed to create database connection: {str(e)}", exc_info=True)
        raise

def test_connection():
    """Test the database connection and print information."""
    try:
        engine = get_db_connection()
        
        # Test the connection
        with engine.connect() as conn:
            # Get database version
            version_result = conn.execute(text("SELECT version()"))
            version = version_result.scalar()
            logger.info(f"Database version: {version}")
            
            # Check if tables exist
            inspector = inspect(engine)
            required_tables = ['folders', 'photos']
            
            for table in required_tables:
                exists = inspector.has_table(table)
                status = "exists" if exists else "does not exist"
                logger.info(f"Table '{table}': {status}")
            
            # Count rows in tables
            for table in required_tables:
                if inspector.has_table(table):
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    logger.info(f"Table '{table}' has {count} rows")
        
        logger.info("Database connection test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    from sqlalchemy import inspect
    success = test_connection()
    sys.exit(0 if success else 1)
