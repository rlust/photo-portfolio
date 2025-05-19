from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import shutil
import os
from datetime import datetime
import uuid
import logging
from .. import models, schemas
from ..database import get_db
from ..config import settings
from ..utils.gcs import gcs_client

# Configure logging
logger = logging.getLogger(__name__)

# Ensure the upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

async def save_file_locally(file: UploadFile) -> Dict[str, Any]:
    """Save an uploaded file locally and return its metadata."""
    file_ext = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "filename": filename,
            "file_path": file_path,
            "content_type": file.content_type,
            "size": os.path.getsize(file_path)
        }
    except Exception as e:
        logger.error(f"Failed to save file locally: {e}")
        return {"success": False, "error": str(e)}

def cleanup_file(file_path: str) -> None:
    """Remove a file if it exists."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.error(f"Failed to clean up file {file_path}: {e}")

@router.post("/upload/", response_model=schemas.Photo, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Upload a photo file to the server or Google Cloud Storage if configured.
    
    Args:
        file: The uploaded file
        folder_id: Optional folder ID to associate the photo with
        
    Returns:
        The created photo record
    """
    # Save file locally first
    local_file = await save_file_locally(file)
    if not local_file["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {local_file.get('error')}"
        )
    
    try:
        file_path = local_file["file_path"]
        filename = local_file["filename"]
        content_type = local_file["content_type"]
        file_size = local_file["size"]
        
        # Determine file URL and path
        file_url = None
        if gcs_client.available and gcs_client.bucket:
            # Upload to GCS
            blob_path = f"photos/{filename}"
            try:
                with open(file_path, "rb") as f:
                    gcs_client.upload_file(
                        f,
                        blob_path,
                        content_type=content_type
                    )
                file_url = f"gs://{gcs_client.bucket_name}/{blob_path}"
                # Schedule local file cleanup
                background_tasks.add_task(cleanup_file, file_path)
            except Exception as e:
                logger.error(f"GCS upload failed, falling back to local storage: {e}")
        
        # If GCS upload failed or not available, use local path
        if not file_url:
            file_url = f"/static/uploads/{filename}"
            # Ensure the static uploads directory exists
            os.makedirs(os.path.join("static", "uploads"), exist_ok=True)
            # Move the file to the static directory
            shutil.move(file_path, os.path.join("static", "uploads", filename))
        
        # Create photo record
        photo_data = {
            "filename": filename,
            "file_path": file_url,
            "content_type": content_type,
            "size": file_size,
            "folder_id": folder_id
        }
        
        db_photo = models.Photo(**photo_data)
        db.add(db_photo)
        db.commit()
        db.refresh(db_photo)
        
        return db_photo
        
    except Exception as e:
        db.rollback()
        # Clean up file in case of error
        cleanup_file(file_path)
        logger.error(f"Error uploading photo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
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
