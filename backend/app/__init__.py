# Initialize the app package
from .config import Base, engine, SessionLocal, get_db
from . import models, schemas

# Import all models to ensure they are registered with SQLAlchemy
from .models.folder import Folder
from .models.photo import Photo

# Import all routes to register them with FastAPI
from .routes import photos, folders

__all__ = [
    'Base', 'engine', 'SessionLocal', 'get_db',
    'models', 'schemas',
    'Folder', 'Photo',
    'photos', 'folders'
]
