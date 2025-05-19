"""Folder model and related functionality."""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config import Base

class Folder(Base):
    """Folder model for organizing photos."""
    __tablename__ = 'folders'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    cover_photo_url = Column(String(1024), nullable=True)
    is_public = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Relationships
    photos = relationship(
        "Photo", 
        back_populates="folder", 
        cascade="save-update, merge, expunge, delete, delete-orphan",
        passive_deletes=True
    )
    owner = relationship("User", back_populates="folders")
    
    def __repr__(self) -> str:
        return f"<Folder(id={self.id}, name='{self.name}')>"
    
    def to_dict(self, include_photos: bool = False) -> Dict[str, Any]:
        """Convert folder object to dictionary.
        
        Args:
            include_photos: If True, include list of photo IDs in the response
            
        Returns:
            Dict containing folder data
        """
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cover_photo_url': self.cover_photo_url,
            'is_public': self.is_public,
            'owner_id': self.owner_id,
            'photo_count': len(self.photos) if hasattr(self, 'photos') else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_photos and hasattr(self, 'photos'):
            result['photos'] = [photo.to_dict() for photo in self.photos]
            
        return result
    
    __table_args__ = (
        # Ensure folder names are unique per user
        Index('ix_folders_owner_name', 'owner_id', 'name', unique=True),
    )
    
    @classmethod
    def create(cls, db: 'Session', obj_in: 'FolderCreate') -> 'Folder':
        """Create a new folder."""
        db_obj = cls(**obj_in.dict(exclude_unset=True))
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @classmethod
    def get(cls, db: 'Session', id: int) -> Optional['Folder']:
        """Get a folder by ID."""
        return db.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def get_by_name(cls, db: 'Session', name: str, owner_id: int) -> Optional['Folder']:
        """Get a folder by name and owner."""
        return db.query(cls).filter(
            cls.name == name,
            cls.owner_id == owner_id
        ).first()
    
    @classmethod
    def get_multi(
        cls, 
        db: 'Session', 
        *, 
        skip: int = 0, 
        limit: int = 100,
        owner_id: Optional[int] = None,
        is_public: Optional[bool] = None
    ) -> List['Folder']:
        """Get multiple folders with optional filtering."""
        query = db.query(cls)
        
        if owner_id is not None:
            query = query.filter(cls.owner_id == owner_id)
        if is_public is not None:
            query = query.filter(cls.is_public == is_public)
            
        return query.offset(skip).limit(limit).all()
    
    @classmethod
    def update(
        cls, 
        db: 'Session', 
        *, 
        db_obj: 'Folder', 
        obj_in: 'FolderUpdate'
    ) -> 'Folder':
        """Update a folder."""
        update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @classmethod
    def delete(cls, db: 'Session', *, id: int) -> None:
        """Delete a folder.
        
        This method explicitly sets folder_id to NULL for all photos in the folder
        before deleting the folder to ensure data consistency.
        """
        # Check if the folder exists first
        folder = db.query(cls).filter_by(id=id).first()
        if not folder:
            return  # Folder doesn't exist, nothing to do
            
        try:
            # First, update all photos in this folder to set folder_id to None
            from app.models.photo import Photo
            db.query(Photo).filter(Photo.folder_id == id).update(
                {Photo.folder_id: None},
                synchronize_session=False
            )
            
            # Now delete the folder
            db.delete(folder)
            db.commit()
            
        except Exception as e:
            # Rollback on error
            db.rollback()
            raise
    
    @classmethod
    def get_user_folders(
        cls, 
        db: 'Session', 
        owner_id: int,
        include_public: bool = False
    ) -> List['Folder']:
        """Get all folders for a user, optionally including public folders."""
        query = db.query(cls).filter(cls.owner_id == owner_id)
        if include_public:
            query = query.filter(cls.is_public == True)  # noqa: E712
        return query.all()

# Pydantic models for request/response schemas
class FolderBase(BaseModel):
    """Base folder schema."""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    cover_photo_url: Optional[HttpUrl] = None
    is_public: bool = True
    owner_id: int

class FolderCreate(FolderBase):
    """Schema for creating a new folder."""
    owner_id: int

class FolderUpdate(BaseModel):
    """Schema for updating a folder."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    cover_photo_url: Optional[HttpUrl] = None
    is_public: Optional[bool] = None

class FolderInDBBase(FolderBase):
    """Base folder schema for database operations."""
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class FolderResponse(FolderInDBBase):
    """Schema for folder responses."""
    photo_count: int = 0
