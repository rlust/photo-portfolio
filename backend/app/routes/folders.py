from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/folders", tags=["folders"])

@router.get("/")
def list_folders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all folders with their photos in a format compatible with the frontend.
    
    Returns a dictionary where keys are folder names and values are arrays of photo objects.
    Example: {"Nature": [{name: "tree.jpg", url: "https://..."}, ...], ...}
    """
    from sqlalchemy.orm import joinedload
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get all folders with their related photos
        folders_with_photos = db.query(models.Folder)\
            .options(joinedload(models.Folder.photos))\
            .offset(skip).limit(limit).all()
        
        # Structure the response as expected by the frontend
        result = {}
        for folder in folders_with_photos:
            # Skip folders without names
            if not folder.name:
                continue
                
            # Create an entry for each folder name
            folder_photos = []
            for photo in folder.photos:
                folder_photos.append({
                    "name": photo.title or photo.filename or f"Photo {photo.id}",
                    "url": photo.url,
                    "id": photo.id,
                    "mimetype": photo.mimetype,
                    "uploaded_at": photo.uploaded_at.isoformat() if photo.uploaded_at else None
                })
            
            # Add folder data to result
            result[folder.name] = folder_photos
            
        return result
    except Exception as e:
        logger.error(f"Error fetching folders: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching folders: {str(e)}"
        )

@router.post("/", response_model=schemas.Folder, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder: schemas.FolderCreate,
    db: Session = Depends(get_db)
):
    """Create a new folder."""
    # Check if folder with same name already exists
    db_folder = db.query(models.Folder).filter(models.Folder.name == folder.name).first()
    if db_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder with this name already exists"
        )
    
    db_folder = models.Folder(**folder.dict())
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder

@router.get("/{folder_id}", response_model=schemas.Folder)
def get_folder(folder_id: int, db: Session = Depends(get_db)):
    """Get a specific folder by ID."""
    db_folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
    if db_folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return db_folder

@router.get("/{folder_id}/photos", response_model=List[schemas.Photo])
def get_folder_photos(
    folder_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all photos in a specific folder."""
    # Check if folder exists
    db_folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
    if db_folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    photos = db.query(models.Photo)\
        .filter(models.Photo.folder_id == folder_id)\
        .offset(skip)\
        .limit(limit)\
        .all()
    return photos

@router.put("/{folder_id}", response_model=schemas.Folder)
def update_folder(
    folder_id: int,
    folder: schemas.FolderUpdate,
    db: Session = Depends(get_db)
):
    """Update a folder."""
    db_folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
    if db_folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Check if new name is already taken
    if folder.name and folder.name != db_folder.name:
        existing_folder = db.query(models.Folder)\
            .filter(models.Folder.name == folder.name)\
            .first()
        if existing_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder with this name already exists"
            )
    
    update_data = folder.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_folder, field, value)
    
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder

@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    """Delete a folder."""
    db_folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
    if db_folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Check if folder has photos
    photo_count = db.query(models.Photo)\
        .filter(models.Photo.folder_id == folder_id)\
        .count()
    
    if photo_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete folder with photos. Delete photos first or move them to another folder."
        )
    
    db.delete(db_folder)
    db.commit()
    return None
