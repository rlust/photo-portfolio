"""Test folder deletion functionality."""
import pytest
from sqlalchemy.orm import Session

from app.models.folder import Folder
from app.models.photo import Photo
from app.models.user import User

@pytest.fixture(scope="function")
def setup_test_data(db_session: Session):
    """Set up test data for folder deletion tests."""
    # Create a test user
    user = User(
        email="test@example.com",
        hashed_password="dummy_hash",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.flush()
    
    # Create a folder
    folder = Folder(
        name="Test Folder",
        description="A test folder",
        owner_id=user.id,
        is_public=True
    )
    db_session.add(folder)
    db_session.flush()
    
    # Create a photo in the folder
    photo = Photo(
        title="Test Photo",
        description="A test photo",
        url="http://example.com/test.jpg",
        owner_id=user.id,
        folder_id=folder.id,
        is_public=True
    )
    db_session.add(photo)
    db_session.commit()
    
    # Refresh objects to ensure we have the latest data
    db_session.refresh(user)
    db_session.refresh(folder)
    db_session.refresh(photo)
    
    return {
        "user": user,
        "folder": folder,
        "photo": photo
    }

def test_folder_deletion(db_session: Session, setup_test_data):
    """Test that deleting a folder sets photo.folder_id to None."""
    try:
        print("\n=== Starting test_folder_deletion ===")
        
        # Get test data from fixture
        test_data = setup_test_data
        folder = test_data["folder"]
        photo = test_data["photo"]
        
        print(f"Test data created:")
        print(f"- Folder: id={folder.id}, name='{folder.name}', owner_id={folder.owner_id}")
        print(f"- Photo: id={photo.id}, title='{photo.title}', folder_id={photo.folder_id}")
        
        # Verify the photo is in the folder
        photo_in_db = db_session.query(Photo).filter_by(id=photo.id).first()
        assert photo_in_db is not None, "Photo not found in database"
        assert photo_in_db.folder_id == folder.id, \
            f"Photo is not in the folder. Expected folder_id: {folder.id}, got: {photo_in_db.folder_id}"
        
        print(f"✅ Verified photo {photo_in_db.id} is in folder {photo_in_db.folder_id}")
        
        # Get all photos in the folder before deletion
        photos_before = db_session.query(Photo).filter(Photo.folder_id == folder.id).all()
        print(f"📸 Found {len(photos_before)} photos in folder before deletion")
        
        # Print photo details before deletion
        for i, p in enumerate(photos_before, 1):
            print(f"  {i}. Photo ID: {p.id}, Title: '{p.title}', Folder ID: {p.folder_id}")
        
        # Delete the folder using the model's delete method
        print(f"\n🗑️  Calling Folder.delete(db_session, id={folder.id})...")
        Folder.delete(db_session, id=folder.id)
        print("✅ Folder.delete() completed")
        
        # Verify the folder was deleted
        deleted_folder = db_session.query(Folder).filter_by(id=folder.id).first()
        assert deleted_folder is None, f"Folder {folder.id} was not deleted"
        print(f"✅ Verified folder {folder.id} was deleted")
        
        # Refresh the session to ensure we get fresh data
        db_session.expire_all()
        print("🔁 Session expired to ensure fresh data")
        
        # Get the photo again after deletion
        photo_after_delete = db_session.query(Photo).filter_by(id=photo.id).first()
        
        # Verify the photo still exists
        assert photo_after_delete is not None, f"Photo {photo.id} was deleted"
        print(f"✅ Verified photo {photo_after_delete.id} still exists")
        
        # Verify the photo's folder_id is None
        assert photo_after_delete.folder_id is None, \
            f"❌ Photo's folder_id was not set to None. Got: {photo_after_delete.folder_id}"
        print(f"✅ Verified photo {photo_after_delete.id} folder_id is now None")
        
        # Get all photos that were in the folder after deletion
        photos_after = db_session.query(Photo).filter(Photo.id.in_([p.id for p in photos_before])).all()
        print(f"📸 Found {len(photos_after)} photos after folder deletion")
        
        # Print photo details after deletion
        for i, p in enumerate(photos_after, 1):
            print(f"  {i}. Photo ID: {p.id}, Title: '{p.title}', Folder ID: {p.folder_id}")
        
        # Verify all photos have folder_id set to None
        for p in photos_after:
            assert p.folder_id is None, f"❌ Photo {p.id} still has folder_id={p.folder_id}"
        
        print("✅ All photos have folder_id set to None")
        print("\n🎉 test_folder_deletion completed successfully!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        print("\n📊 Current database state:")
        print("📂 Folders:")
        for f in db_session.query(Folder).all():
            print(f"  - ID: {f.id}, Name: '{f.name}', Owner: {f.owner_id}")
        print("🖼️  Photos:")
        for p in db_session.query(Photo).all():
            print(f"  - ID: {p.id}, Title: '{p.title}', Folder ID: {p.folder_id}, Owner: {p.owner_id}")
        raise

# This allows running the test directly with python -m pytest tests/test_folder_delete.py -v -s
if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
