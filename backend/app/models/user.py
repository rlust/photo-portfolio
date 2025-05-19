"""User model and related functionality."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.security import get_password_hash, verify_password

from app.config import Base

class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    is_superuser = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    photos = relationship("Photo", back_populates="owner", cascade="all, delete-orphan")
    folders = relationship("Folder", back_populates="owner", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        # This is a placeholder. In a real app, you would use a proper password hashing library
        # like passlib with bcrypt or argon2
        return self.hashed_password == password
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user object to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create(cls, db: 'Session', obj_in: 'UserCreate') -> 'User':
        """Create a new user."""
        
        db_obj = cls(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            is_active=True,
            is_superuser=False
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @classmethod
    def get(cls, db: 'Session', id: int) -> Optional['User']:
        """Get a user by ID."""
        return db.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def get_by_email(cls, db: 'Session', email: str) -> Optional['User']:
        """Get a user by email."""
        return db.query(cls).filter(cls.email == email).first()
    
    @classmethod
    def update(cls, db: 'Session', db_obj: 'User', obj_in: 'UserUpdate') -> 'User':
        """Update a user."""
        update_data = obj_in.dict(exclude_unset=True)
        if 'password' in update_data and update_data['password']:
            update_data['hashed_password'] = get_password_hash(update_data.pop('password'))
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @classmethod
    def delete(cls, db: 'Session', id: int) -> None:
        """Delete a user."""
        db_obj = db.query(cls).get(id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
    
    @classmethod
    def authenticate(cls, db: 'Session', email: str, password: str) -> Optional['User']:
        """Authenticate a user."""
        user = cls.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

# Pydantic models for request/response schemas
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None

class UserInDBBase(UserBase):
    """Base user schema for database operations."""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserResponse(UserInDBBase):
    """Schema for user responses (without sensitive data)."""
    pass

class UserInDB(UserInDBBase):
    """User model for database operations."""
    hashed_password: str
