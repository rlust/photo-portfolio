from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
from datetime import datetime
import uuid
from .. import models, schemas
from ..database import get_db
from ..config import settings
from ..utils.gcs import gcs_client

# Ensure the upload directory exists
os.makedirs("uploads", exist_ok=True)

router = APIRouter(prefix="/api/photos", tags=["photos"])

@router.get("/", response_model=List[schemas.Photo])
def list_photos(
    skip: int = 0,
    limit: int = 100,
    folder_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List all photos with optional folder filtering."""
    query = db.query(models.Photo)
    if folder_id is not None:
        query = query.filter(models.Photo.folder_id == folder_id)
    photos = query.offset(skip).limit(limit).all()
    return photos

@router.post("/", response_model=schemas.Photo, status_code=status.HTTP_201_CREATED)
def create_photo(
    photo: schemas.PhotoCreate,
    db: Session = Depends(get_db)
):
    """Create a new photo."""
    db_photo = models.Photo(**photo.dict())
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    return db_photo

@router.post("/upload/", response_model=schemas.Photo, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    folder_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Upload a photo file to Google Cloud Storage.
    
    Args:
        file: The uploaded file
        folder_id: Optional ID of the folder to associate with the photo
        db: Database session
        
    Returns:
        The created photo record
    """
    if not gcs_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GCS client not configured"
        )
    
    try:
        # Generate a unique filename
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_id = str(uuid.uuid4())
        filename = f"photos/{unique_id}{file_extension}"
        
        # Upload to GCS
        file.file.seek(0)  # Ensure we're at the start of the file
        public_url = gcs_client.upload_file(
            file_obj=file.file,
            destination_blob_name=filename,
            content_type=file.content_type,
            metadata={
                'original_filename': file.filename,
                'uploaded_by': 'api',
            }
        )
        
        # Create photo record in database
        photo_data = {
            "title": file.filename,
            "url": public_url,
            "mimetype": file.content_type,
            "folder_id": folder_id,
            "storage_path": filename  # Store the GCS path for future reference
        }
        
        db_photo = models.Photo(**photo_data)
        db.add(db_photo)
        db.commit()
        db.refresh(db_photo)
        
        return db_photo
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading photo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload photo: {str(e)}"
        )

@router.get("/{photo_id}", response_model=schemas.Photo)
def get_photo(photo_id: int, db: Session = Depends(get_db)):
    """Get a specific photo by ID."""
    db_photo = db.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if db_photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    return db_photo

@router.put("/{photo_id}", response_model=schemas.Photo)
def update_photo(
    photo_id: int,
    photo: schemas.PhotoUpdate,
    db: Session = Depends(get_db)
):
    """Update a photo."""
    db_photo = db.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if db_photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    update_data = photo.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_photo, field, value)
    
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    return db_photo

@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    """Delete a photo."""
    db_photo = db.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if db_photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Delete the file if it exists
    if db_photo.url and db_photo.url.startswith("/static/"):
        file_path = os.path.join("static", os.path.basename(db_photo.url))
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.delete(db_photo)
    db.commit()
    return None
