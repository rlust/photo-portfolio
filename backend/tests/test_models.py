"""Tests for database models."""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.photo import Photo


def test_user_model(db_session):
    """Test User model creation and relationships."""
    # Create a test user
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    
    db_session.add(user)
    db_session.commit()
    
    # Test user attributes
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.photos == []
    assert user.folders == []
    assert isinstance(user.created_at, datetime)
    assert user.updated_at is None  # updated_at should be None initially
    
    # Test string representation
    assert "test@example.com" in str(user)
    
    # Test password hashing
    # The current implementation just compares the strings directly for testing
    assert user.verify_password("hashed_password_123") is True
    assert user.verify_password("wrong_password") is False
    
    # Test to_dict method
    user_dict = user.to_dict()
    assert user_dict["email"] == "test@example.com"
    assert user_dict["full_name"] == "Test User"


def test_photo_model(db_session, test_user):
    """Test Photo model creation and relationships."""
    # Create a test photo
    photo = Photo(
        title="Test Photo",
        description="A test photo",
        url="http://example.com/test.jpg",
        file_size=1024,
        mimetype="image/jpeg",
        width=800,
        height=600,
        owner_id=test_user.id,
        is_public=True,
        storage_path="test/test.jpg"
    )
    
    db_session.add(photo)
    db_session.commit()
    
    # Test photo attributes
    assert photo.title == "Test Photo"
    assert photo.description == "A test photo"
    assert photo.url == "http://example.com/test.jpg"
    assert photo.file_size == 1024
    assert photo.mimetype == "image/jpeg"
    assert photo.width == 800
    assert photo.height == 600
    assert photo.owner_id == test_user.id
    assert photo.is_public is True
    assert photo.storage_path == "test/test.jpg"
    assert isinstance(photo.uploaded_at, datetime)
    
    # Test string representation
    assert "Test Photo" in str(photo)


def test_photo_required_fields(db_session, test_user):
    """Test that required fields are enforced."""
    # Test missing required fields
    with pytest.raises(IntegrityError):
        photo = Photo()
        db_session.add(photo)
        db_session.commit()
    
    db_session.rollback()
    
    # Test with minimal required fields
    photo = Photo(
        url="http://example.com/test.jpg",
        file_size=1024,
        mimetype="image/jpeg",
        owner_id=test_user.id,
        is_public=True
    )
    db_session.add(photo)
    db_session.commit()
    
    assert photo.id is not None
    assert photo.title is None
    assert photo.description is None
    assert photo.width is None
    assert photo.height is None
    assert photo.storage_path is None
    
    # Clean up
    db_session.delete(photo)
    db_session.commit()


def test_user_photo_relationship(db_session, test_user):
    """Test the relationship between User and Photo models."""
    # Create test photos
    photo1 = Photo(
        title="Photo 1",
        url="http://example.com/photo1.jpg",
        file_size=1024,
        mimetype="image/jpeg",
        owner_id=test_user.id,
        is_public=True
    )
    photo2 = Photo(
        title="Photo 2",
        url="http://example.com/photo2.jpg",
        file_size=2048,
        mimetype="image/png",
        owner_id=test_user.id,
        is_public=True
    )
    
    db_session.add_all([photo1, photo2])
    db_session.commit()
    
    # Test relationship
    assert len(test_user.photos) == 2
    assert photo1 in test_user.photos
    assert photo2 in test_user.photos
    assert photo1.owner == test_user
    assert photo2.owner == test_user


def test_photo_deletion_cascade(db_session, test_user):
    """Test that photos are deleted when a user is deleted."""
    # Create a test photo
    photo = Photo(
        title="Test Photo",
        url="http://example.com/test.jpg",
        file_size=1024,
        mimetype="image/jpeg",
        owner_id=test_user.id,
        is_public=True
    )
    db_session.add(photo)
    db_session.commit()
    
    # Store photo ID for later verification
    photo_id = photo.id
    
    # Delete the user
    db_session.delete(test_user)
    db_session.commit()
    
    # Verify photo was deleted
    assert db_session.get(Photo, photo_id) is None
