"""Integration tests for database operations."""
import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import HttpUrl

from app.models.user import User, UserCreate, UserUpdate
from app.models.photo import Photo, PhotoCreate, PhotoUpdate
from app.models.folder import Folder, FolderCreate, FolderUpdate
from app.database import get_db
from app.security import get_password_hash, verify_password


def test_user_crud_operations(db_session: Session):
    """Test CRUD operations for User model."""
    # Create a test user
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User"
    )
    
    # Test create
    user = User.create(db_session, user_data)
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active is True
    assert user.is_superuser is False
    assert verify_password("testpassword123", user.hashed_password)
    
    # Test get by id
    user_by_id = User.get(db_session, user.id)
    assert user_by_id.id == user.id
    
    # Test get by email
    user_by_email = User.get_by_email(db_session, email="test@example.com")
    assert user_by_email.id == user.id
    
    # Test update
    update_data = UserUpdate(
        full_name="Updated User",
        is_active=False
    )
    updated_user = User.update(db_session, db_obj=user, obj_in=update_data)
    assert updated_user.full_name == "Updated User"
    assert updated_user.is_active is False
    
    # Test authenticate
    authenticated_user = User.authenticate(
        db_session, 
        email="test@example.com", 
        password="testpassword123"
    )
    assert authenticated_user is not None
    
    # Test delete
    User.delete(db_session, id=user.id)
    deleted_user = User.get(db_session, user.id)
    assert deleted_user is None


def test_photo_crud_operations(db_session: Session, test_user: User):
    """Test CRUD operations for Photo model."""
    # Create a test photo
    photo_data = PhotoCreate(
        title="Test Photo",
        description="A test photo",
        url=HttpUrl("http://example.com/photo.jpg"),
        mimetype="image/jpeg",
        file_size=1024,
        width=800,
        height=600,
        is_public=True,
        owner_id=test_user.id,
        location_tag="Test Location"
    )
    
    # Test create
    photo = Photo.create(db_session, obj_in=photo_data)
    assert photo.id is not None
    assert photo.title == "Test Photo"
    assert photo.description == "A test photo"
    assert photo.url == "http://example.com/photo.jpg"
    assert photo.owner_id == test_user.id
    assert photo.is_public is True
    
    # Test get by id
    photo_by_id = Photo.get(db_session, photo.id)
    assert photo_by_id.id == photo.id
    
    # Test update
    update_data = PhotoUpdate(
        title="Updated Photo",
        description="Updated description",
        is_public=False
    )
    updated_photo = Photo.update(db_session, db_obj=photo, obj_in=update_data)
    assert updated_photo.title == "Updated Photo"
    assert updated_photo.description == "Updated description"
    assert updated_photo.is_public is False
    
    # Test get by owner
    user_photos = Photo.get_by_owner(db_session, owner_id=test_user.id)
    assert len(user_photos) == 1
    assert user_photos[0].id == photo.id
    
    # Test delete
    Photo.delete(db_session, id=photo.id)
    deleted_photo = Photo.get(db_session, photo.id)
    assert deleted_photo is None


def test_folder_crud_operations(db_session: Session, test_user: User):
    """Test CRUD operations for Folder model."""
    # Create a test folder
    folder_data = FolderCreate(
        name="Test Folder",
        description="A test folder",
        is_public=False,
        owner_id=test_user.id
    )
    
    # Test create
    folder = Folder.create(db_session, obj_in=folder_data)
    assert folder.id is not None
    assert folder.name == "Test Folder"
    assert folder.description == "A test folder"
    assert folder.owner_id == test_user.id
    assert folder.is_public is False
    
    # Test get by id
    folder_by_id = Folder.get(db_session, folder.id)
    assert folder_by_id.id == folder.id
    
    # Test update
    update_data = FolderUpdate(
        name="Updated Folder",
        description="Updated description",
        is_public=True
    )
    updated_folder = Folder.update(db_session, db_obj=folder, obj_in=update_data)
    assert updated_folder.name == "Updated Folder"
    assert updated_folder.description == "Updated description"
    assert updated_folder.is_public is True
    
    # Test get by owner
    user_folders = Folder.get_by_owner(db_session, owner_id=test_user.id)
    assert len(user_folders) == 1
    assert user_folders[0].id == folder.id
    
    # Test delete
    Folder.delete(db_session, id=folder.id)
    deleted_folder = Folder.get(db_session, folder.id)
    assert deleted_folder is None


def test_photo_folder_relationship(db_session: Session, test_user: User):
    """Test the relationship between photos and folders."""
    print("\n=== Starting test_photo_folder_relationship ===")
    
    # Start a transaction for this test
    transaction = db_session.begin_nested()
    print("Started nested transaction")
    
    try:
        print("\n=== Creating test data ===")
        # Create a folder
        folder_data = FolderCreate(
            name="Test Folder",
            description="A test folder",
            owner_id=test_user.id
        )
        print(f"Creating folder with data: {folder_data}")
        
        folder = Folder.create(db_session, obj_in=folder_data)
        db_session.flush()  # Ensure folder is created before we reference it
        print(f"Created folder: {folder.id}")
        
        # Create a photo in the folder
        photo_data = PhotoCreate(
            title="Test Photo in Folder",
            url="http://example.com/photo_in_folder.jpg",
            mimetype="image/jpeg",
            owner_id=test_user.id,
            folder_id=folder.id
        )
        print(f"Creating photo with data: {photo_data}")
        
        photo = Photo.create(db_session, obj_in=photo_data)
        db_session.flush()  # Ensure photo is created
        print(f"Created photo: {photo.id} in folder: {photo.folder_id}")
        
        # Commit the initial creation
        db_session.commit()
        print("Committed initial data creation")
        
        # Start a new transaction for the test
        transaction = db_session.begin_nested()
        
        # Refresh objects to ensure we have the latest state
        db_session.refresh(folder)
        db_session.refresh(photo)
        print("Refreshed folder and photo objects")
        
        # Test relationship
        print("\n=== Testing photo-folder relationship ===")
        print(f"Photo ID: {photo.id}, Folder ID: {photo.folder_id}")
        print(f"Expected Folder ID: {folder.id}")
        assert photo.folder_id == folder.id, f"Photo's folder_id ({photo.folder_id}) does not match folder.id ({folder.id})"
        
        # Refresh folder to get updated photos collection
        db_session.refresh(folder)
        photo_ids = [p.id for p in folder.photos]
        print(f"Photos in folder: {photo_ids}")
        print(f"Looking for photo ID: {photo.id}")
        
        # Verify the photo is in the folder's photos collection
        assert photo in folder.photos, f"Photo {photo.id} not found in folder's photos"
        
        # Test folder deletion
        print("\n=== Testing folder deletion ===")
        print("Before delete:")
        print(f"  - Folder exists: {Folder.get(db_session, folder.id) is not None}")
        print(f"  - Photo exists: {Photo.get(db_session, photo.id) is not None}")
        print(f"  - Photo folder_id: {photo.folder_id}")
        
        # Delete the folder using the model's delete method
        print("\nCalling Folder.delete()...")
        Folder.delete(db_session, id=folder.id)
        print("Folder.delete() completed")
        
        # Verify folder was deleted
        deleted_folder = Folder.get(db_session, folder.id)
        print("\nAfter delete:")
        print(f"  - Folder exists: {deleted_folder is not None}")
        
        # Photo should still exist but with folder_id set to None
        photo_after_delete = Photo.get(db_session, photo.id)
        print(f"  - Photo exists: {photo_after_delete is not None}")
        
        if photo_after_delete:
            print(f"  - Photo folder_id: {photo_after_delete.folder_id}")
            
            # Check if the photo still exists in the database
            photo_count = db_session.query(Photo).filter(Photo.id == photo.id).count()
            print(f"  - Photo count in database: {photo_count}")
            
            # Check the photo's folder_id directly from the database
            db_photo = db_session.query(Photo).filter(Photo.id == photo.id).first()
            print(f"  - Photo from direct query - id: {db_photo.id}, folder_id: {db_photo.folder_id}")
            
            # Verify the photo's folder_id was set to None
            assert photo_after_delete.folder_id is None, \
                f"Photo's folder_id was not set to None after folder deletion. Got: {photo_after_delete.folder_id}"
        
        # Verify photo still exists
        assert photo_after_delete is not None, "Photo was deleted when folder was deleted"
        
        # Verify folder was actually deleted
        assert deleted_folder is None, "Folder was not deleted"
        
        print("\n=== Test completed successfully ===")
        
    except Exception as e:
        print(f"\n=== Test failed with error ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        db_session.rollback()
        raise
    finally:
        # Always rollback the nested transaction to clean up
        db_session.rollback()


def test_user_photo_relationship(db_session: Session, test_user: User):
    """Test the relationship between users and photos."""
    # Create multiple photos for the test user
    for i in range(3):
        Photo.create(
            db_session,
            obj_in=PhotoCreate(
                title=f"Test Photo {i}",
                url=f"http://example.com/photo_{i}.jpg",
                mimetype="image/jpeg",
                owner_id=test_user.id
            )
        )
    
    # Test relationship
    assert len(test_user.photos) == 3
    assert all(photo.owner_id == test_user.id for photo in test_user.photos)
    
    # Test cascade delete
    db_session.delete(test_user)
    db_session.commit()
    
    # Photos should be deleted due to cascade
    photos_after_delete = db_session.query(Photo).filter_by(owner_id=test_user.id).all()
    assert len(photos_after_delete) == 0
