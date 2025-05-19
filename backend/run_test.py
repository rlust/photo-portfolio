import sys
import logging
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from app.database import Base, SessionLocal, init_db, engine
from app.models.user import User
from tests.test_database_operations import test_photo_folder_relationship

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def setup_database():
    """Set up the database and create tables."""
    try:
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise

def create_test_user(db) -> User:
    """Create a test user if one doesn't exist."""
    try:
        user = db.query(User).first()
        if not user:
            logger.info("Creating test user...")
            user = User(
                email="test@example.com",
                hashed_password="dummy_hash",  # In a real app, use get_password_hash
                full_name="Test User",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created test user with ID: {user.id}")
        else:
            logger.info(f"Using existing test user with ID: {user.id}")
        return user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating test user: {e}")
        raise

def main():
    """Main function to run the test."""
    logger.info("Starting test...")
    db = None
    
    try:
        # Set up the database
        setup_database()
        
        # Create a new session
        db = SessionLocal()
        
        # Create test user
        user = create_test_user(db)
        
        logger.info(f"Running test with user ID: {user.id}")
        
        # Run the test
        test_photo_folder_relationship(db, user)
        
        logger.info("Test completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return 1
    finally:
        if db:
            try:
                db.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

if __name__ == "__main__":
    sys.exit(main())
