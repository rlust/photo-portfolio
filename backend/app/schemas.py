from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field

# Shared properties
class FolderBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    cover_photo_url: Optional[str] = None
    is_public: bool = True

# Properties to receive on folder creation
class FolderCreate(FolderBase):
    pass

# Properties to receive on folder update
class FolderUpdate(FolderBase):
    name: Optional[str] = Field(None, max_length=255)
    is_public: Optional[bool] = None

# Properties shared by models stored in DB
class FolderInDBBase(FolderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Properties to return to client
class Folder(FolderInDBBase):
    pass

# Shared properties for Photo
class PhotoBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    url: str
    mimetype: Optional[str] = None
    gcs_path: Optional[str] = None
    location_tag: Optional[str] = None
    is_public: bool = True
    folder_id: Optional[int] = None

# Properties to receive on photo creation
class PhotoCreate(PhotoBase):
    pass

# Properties to receive on photo update
class PhotoUpdate(PhotoBase):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    folder_id: Optional[int] = None

# Properties shared by models stored in DB
class PhotoInDBBase(PhotoBase):
    id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

# Properties to return to client
class Photo(PhotoInDBBase):
    pass

# Additional response models
class FolderWithPhotos(Folder):
    photos: List[Photo] = []

    class Config:
        from_attributes = True
