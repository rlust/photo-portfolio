import os
import sys
from sqlalchemy import create_engine, text, exc
from sqlalchemy_utils import database_exists, create_database, drop_database
from app import app, Base, get_db_uri, engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def reset_database():
    """Drop and recreate the database with the current schema."""
    try:
        # Get database connection parameters from environment variables
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME')
        
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Missing required database environment variables")
        
        # Create a connection to the postgres database (default database)
        temp_uri = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/postgres"
        engine_temp = create_engine(temp_uri, isolation_level='AUTOCOMMIT')
        
        # Drop the database if it exists
        with engine_temp.connect() as conn:
            # Disconnect all other connections
            conn.execute(text(
                f"SELECT pg_terminate_backend(pg_stat_activity.pid) "
                f"FROM pg_stat_activity "
                f"WHERE pg_stat_activity.datname = '{db_name}' "
                f"AND pid <> pg_backend_pid();"
            ))
            
            # Drop and recreate the database
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE)"))
            print(f"Dropped database: {db_name}")
            
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"Created database: {db_name}")
        
        # Now create all tables with the new schema
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("Database reset successfully!")
        
        return True
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("WARNING: This will DROP and RECREATE the database. All data will be lost!")
    print("Resetting database...")
    if reset_database():
        print("Database reset completed successfully!")
    else:
        print("Failed to reset database.")
