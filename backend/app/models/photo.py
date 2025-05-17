from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..config import Base

class Photo(Base):
    __tablename__ = 'photos'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    url = Column(String(1024), nullable=False, index=True)
    mimetype = Column(String(128), nullable=True)
    gcs_path = Column(String(1024), nullable=True, index=True)  # Legacy field, use storage_path instead
    storage_path = Column(String(1024), nullable=True, index=True)  # Path to the file in GCS
    uploaded_at = Column(DateTime, server_default=func.now(), index=True)
    location_tag = Column(String(255), nullable=True, index=True)
    is_public = Column(Boolean, default=True, index=True)
    
    # Foreign key to Folder
    folder_id = Column(Integer, ForeignKey('folders.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Relationships
    folder = relationship("Folder", back_populates="photos")
    
    def __repr__(self):
        return f"<Photo(id={self.id}, title='{self.title}')>"
    
    __table_args__ = (
        # Add composite index for common query patterns
        Index('ix_photos_folder_public', 'folder_id', 'is_public'),
        Index('ix_photos_uploaded_public', 'uploaded_at', 'is_public'),
    )
