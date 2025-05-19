"""Models package for the Photo Portfolio application.

This package contains all the database models and related schemas for the application.
"""
from .user import (
    User,
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserResponse,
    UserInDBBase
)
from .photo import (
    Photo,
    PhotoBase,
    PhotoCreate,
    PhotoUpdate,
    PhotoInDBBase,
    PhotoResponse
)
from .folder import (
    Folder,
    FolderBase,
    FolderCreate,
    FolderUpdate,
    FolderInDBBase,
    FolderResponse
)

# Make models available at package level
__all__ = [
    # User models
    'User', 'UserBase', 'UserCreate', 'UserUpdate', 'UserInDB', 'UserResponse', 'UserInDBBase',
    # Photo models
    'Photo', 'PhotoBase', 'PhotoCreate', 'PhotoUpdate', 'PhotoInDBBase', 'PhotoResponse',
    # Folder models
    'Folder', 'FolderBase', 'FolderCreate', 'FolderUpdate', 'FolderInDBBase', 'FolderResponse',
]
