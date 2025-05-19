# Initialize the app package
from .config import Base, engine, SessionLocal, get_db, settings
from . import models, schemas
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all models to ensure they are registered with SQLAlchemy
from .models.folder import Folder
from .models.photo import Photo

# Import routes (GCS client will be initialized lazily when needed)
try:
    from .routes import photos, folders
    ROUTERS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Failed to import some routes: {e}")
    ROUTERS_AVAILABLE = False

__all__ = [
    'Base', 'engine', 'SessionLocal', 'get_db', 'settings',
    'models', 'schemas',
    'Folder', 'Photo'
]

# Conditionally add routers to __all__ if they were imported successfully
if ROUTERS_AVAILABLE:
    __all__.extend(['photos', 'folders'])
