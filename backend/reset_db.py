#!/usr/bin/env python3
"""
Database reset utility for the Photo Portfolio application.

This script provides functionality to reset the database to a clean state,
dropping all tables and recreating them. It's primarily used for development
and testing purposes.
"""
import os
import sys
import logging
import argparse
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Reset the Photo Portfolio database.')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    parser.add_argument(
        '--drop-db',
        action='store_true',
        help='Drop and recreate the entire database (requires superuser privileges)'
    )
    parser.add_argument(
        '--env',
        type=str,
        default='.env',
        help='Path to .env file (default: .env)'
    )
    return parser.parse_args()

def confirm_reset() -> bool:
    """Prompt for confirmation before resetting the database."""
    print("\nWARNING: This will delete all data in the database!")
    response = input("Are you sure you want to continue? [y/N] ").strip().lower()
    return response in ('y', 'yes')

def reset_database(drop_db: bool = False) -> bool:
    """
    Reset the database to a clean state.
    
    Args:
        drop_db: If True, drop and recreate the entire database.
                If False, only drop and recreate all tables.
    
    Returns:
        bool: True if the reset was successful, False otherwise
    """
    try:
        # Import here to ensure environment variables are loaded first
        from app.database import reset_db, drop_and_recreate_db
        from app.config import settings, engine, Base
        
        if drop_db:
            logger.warning("Dropping and recreating the entire database...")
            success = drop_and_recreate_db()
        else:
            logger.warning("Dropping and recreating all tables...")
            success = reset_db()
        
        if success:
            logger.info("Database reset completed successfully.")
        else:
            logger.error("Failed to reset database.")
        
        return success
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Make sure you're running this script from the correct directory.")
        return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return False

def main():
    """Main entry point for the reset_db script."""
    args = parse_args()
    
    # Load environment variables
    if os.path.exists(args.env):
        from dotenv import load_dotenv
        load_dotenv(args.env)
        logger.info(f"Loaded environment variables from {args.env}")
    
    # Check if we should proceed with the reset
    if not args.force and not confirm_reset():
        logger.info("Database reset cancelled.")
        return 0
    
    # Perform the reset
    success = reset_database(args.drop_db)
    return 0 if success else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred:")
        sys.exit(1)
