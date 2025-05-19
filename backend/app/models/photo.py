"""Photo model and related functionality."""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config import Base

class Photo(Base):
    """Photo model for storing image metadata."""
    __tablename__ = 'photos'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    url = Column(String(1024), nullable=False, index=True)
    mimetype = Column(String(128), nullable=True)
    file_size = Column(BigInteger, nullable=True)  # File size in bytes
    width = Column(Integer, nullable=True)  # Image width in pixels
    height = Column(Integer, nullable=True)  # Image height in pixels
    gcs_path = Column(String(1024), nullable=True, index=True)  # Legacy field, use storage_path instead
    storage_path = Column(String(1024), nullable=True, index=True)  # Path to the file in GCS
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    location_tag = Column(String(255), nullable=True, index=True)
    is_public = Column(Boolean, default=True, index=True)
    
    # Foreign keys
    folder_id = Column(Integer, ForeignKey('folders.id', ondelete='SET NULL'), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Relationships
    folder = relationship("Folder", back_populates="photos")
    owner = relationship("User", back_populates="photos")
    
    def __repr__(self) -> str:
        return f"<Photo(id={self.id}, title='{self.title}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert photo object to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "mimetype": self.mimetype,
            "file_size": self.file_size,
            "width": self.width,
            "height": self.height,
            "storage_path": self.storage_path or self.gcs_path,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "location_tag": self.location_tag,
            "is_public": self.is_public,
            "folder_id": self.folder_id,
            "owner_id": self.owner_id
        }
    
    __table_args__ = (
        # Add composite index for common query patterns
        Index('ix_photos_folder_public', 'folder_id', 'is_public'),
        Index('ix_photos_uploaded_public', 'uploaded_at', 'is_public'),
        Index('ix_photos_owner_public', 'owner_id', 'is_public'),
    )
    
    @classmethod
    def create(cls, db: 'Session', obj_in: 'PhotoCreate') -> 'Photo':
        """Create a new photo."""
        data = obj_in.dict(exclude_unset=True)
        # Convert HttpUrl to string if needed
        if 'url' in data and hasattr(data['url'], 'url'):
            data['url'] = data['url'].url
        # Ensure owner_id is set
        if 'owner_id' not in data:
            raise ValueError("owner_id is required to create a photo")
        db_obj = cls(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @classmethod
    def get(cls, db: 'Session', id: int) -> Optional['Photo']:
        """Get a photo by ID."""
        return db.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def get_multi(
        cls, 
        db: 'Session', 
        *, 
        skip: int = 0, 
        limit: int = 100,
        owner_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        is_public: Optional[bool] = None
    ) -> List['Photo']:
        """Get multiple photos with optional filtering."""
        query = db.query(cls)
        
        if owner_id is not None:
            query = query.filter(cls.owner_id == owner_id)
        if folder_id is not None:
            query = query.filter(cls.folder_id == folder_id)
        if is_public is not None:
            query = query.filter(cls.is_public == is_public)
            
        return query.offset(skip).limit(limit).all()
    
    @classmethod
    def update(
        cls, 
        db: 'Session', 
        *, 
        db_obj: 'Photo', 
        obj_in: 'PhotoUpdate'
    ) -> 'Photo':
        """Update a photo."""
        update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @classmethod
    def delete(cls, db: 'Session', *, id: int) -> None:
        """Delete a photo."""
        db_obj = db.query(cls).get(id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
    
    @classmethod
    def get_by_owner(
        cls,
        db: 'Session',
        owner_id: int
    ) -> List['Photo']:
        """Get all photos owned by a user."""
        return db.query(cls).filter(cls.owner_id == owner_id).all()
    
    @classmethod
    def get_by_owner_and_folder(
        cls, 
        db: 'Session', 
        owner_id: int, 
        folder_id: Optional[int] = None
    ) -> List['Photo']:
        """Get photos by owner and optionally by folder."""
        query = db.query(cls).filter(cls.owner_id == owner_id)
        if folder_id is not None:
            query = query.filter(cls.folder_id == folder_id)
        return query.all()

# Pydantic models for request/response schemas
class PhotoBase(BaseModel):
    """Base photo schema."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    url: HttpUrl
    mimetype: Optional[str] = None
    file_size: Optional[int] = Field(None, ge=0)
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)
    is_public: bool = True
    location_tag: Optional[str] = None
    folder_id: Optional[int] = None
    owner_id: int

class PhotoCreate(PhotoBase):
    """Schema for creating a new photo."""
    owner_id: int

class PhotoUpdate(BaseModel):
    """Schema for updating a photo."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    location_tag: Optional[str] = None
    folder_id: Optional[int] = None

class PhotoInDBBase(PhotoBase):
    """Base photo schema for database operations."""
    id: int
    owner_id: int
    uploaded_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PhotoResponse(PhotoInDBBase):
    """Schema for photo responses."""
    pass
