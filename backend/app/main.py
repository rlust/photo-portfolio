import sys
try:
    import os
    import logging
    import sqlalchemy
    import datetime
    from fastapi import FastAPI, Depends, status, HTTPException, BackgroundTasks, UploadFile, File, Form
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from sqlalchemy.orm import Session
    from typing import List, Optional, Dict, Any

    from .config import Base, get_db, settings
    engine = None
    from .database import init_db, reset_db
    from . import models, schemas

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Try to import routes (they may fail if GCS dependencies are not available)
    ROUTERS = {}
    try:
        from .routes import photos, folders
        from .utils.gcs import gcs_client
        ROUTERS['photos'] = photos.router
        ROUTERS['folders'] = folders.router
    except ImportError as e:
        logger.warning(f"Failed to import some routes: {e}")
        gcs_client = None
except Exception as e:
    print("[FATAL_IMPORT_ERROR]", e, file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise


# Initialize FastAPI app
app = FastAPI(
    title="Photo Portfolio API",
    description="API for managing photo portfolios",
    version="1.0.0",
    # Disable automatic redirect when trailing slash is missing
    redirect_slashes=False
)

@app.get("/", tags=["health"])
async def root():
    """Root endpoint that responds to Cloud Run health checks.
    
    This endpoint ensures that Cloud Run's default health check system will succeed,
    preventing 503 errors. For detailed health information, use /api/health instead.
    
    Returns:
        dict: A simple message indicating the API is running.
    """
    return {
        "status": "online",
        "message": "Photo Portfolio API is running",
        "endpoints": {
            "health": "/api/health",
            "docs": "/docs"
        }
    }

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database initialization with retry logic
@app.on_event("startup")
async def startup_event():
    import asyncio
    global engine
    max_retries = 5
    retry_delay = 2  # seconds
    for attempt in range(1, max_retries + 1):
        try:
            from .config import create_db_engine
            engine = create_db_engine(settings)
            if engine is not None:
                from .config import Base
                Base.metadata.create_all(bind=engine)
                logger.info("Database initialized successfully.")
                break
            else:
                logger.error("Database engine is None. Skipping DB initialization.")
                raise Exception("Database engine is None")
        except Exception as e:
            logger.error(f"Database connection error (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                logger.error("Max retries reached. Failed to connect to the database.")
                # Continue without raising to allow app to start with DB down
                break
            logger.info(f"Retrying in {retry_delay} seconds...")
            import time
            time.sleep(retry_delay)

# Health check endpoint with detailed status
@app.get("/api/health")
async def health_check():
    from sqlalchemy import text
    from .database import SessionLocal
    import socket
    import time
    
    # Initialize response
    response = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": "disconnected",
            "error": None,
            "response_time_ms": None
        },
        "system": {
            "hostname": socket.gethostname(),
            "platform": os.uname().sysname,
            "python_version": ".".join(map(str, sys.version_info[:3]))
        },
        "services": {
            "database": False,
            "storage": False
        }
    }
    
    # Check database connection
    db = None
    start_time = time.time()
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            response["database"]["status"] = "connected"
            response["services"]["database"] = True
        else:
            response["database"]["error"] = "Unexpected database response"
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        response["database"]["error"] = str(e)
        response["status"] = "degraded"
    finally:
        if db:
            db.close()
            response["database"]["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Check storage connection if GCS is configured using the existing client
    if settings.GCS_BUCKET and gcs_client and gcs_client.available:
        try:
            # Use our improved GCS client that works with workload identity
            # Just check if we can list a small number of files to verify access
            files = gcs_client.list_files(prefix="photos/", max_results=1)
            if files is not None:  # If we get any response (even empty list), connection works
                response["services"]["storage"] = True
                logger.info(f"Storage health check passed, found {len(files)} files")
        except Exception as e:
            logger.error(f"Storage health check error: {e}")
            response["status"] = "degraded"
    
    # If any required service is down, mark as unhealthy
    if not all(response["services"].values()):
        response["status"] = "unhealthy"
    
    return response

# Reset database endpoint (for development only)
@app.post("/api/reset-db")
async def reset_database():
    if os.getenv("ENV") != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )
    reset_db()
    return {"message": "Database reset successfully"}

# GCS reindexing endpoint to populate database from cloud storage
@app.post("/api/reindex-gcs")
async def reindex_gcs(background_tasks: BackgroundTasks):
    """
    Scan Google Cloud Storage bucket and add all images to the database.
    This is useful for initial database population or recovery.
    """
    logger.info("Starting GCS bucket reindexing operation")
    
    # Check if the storage is available
    if not gcs_client or not gcs_client.available:
        logger.error("GCS client is not available. Cannot reindex.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Cloud Storage is not properly configured"
        )
    
    try:
        # Connect to the database
        db = next(get_db())
        
        # Get list of existing photos with gcs_path field set
        existing_photos = db.query(models.Photo).filter(models.Photo.gcs_path != None).all()
        existing_paths = {photo.gcs_path for photo in existing_photos}
        logger.info(f"Found {len(existing_photos)} existing photos in database")
        
        # Get list of all files in GCS bucket
        all_files = gcs_client.list_files(prefix='photos/')
        logger.info(f"Found {len(all_files)} images in GCS bucket with prefix 'photos/'")
        
        # Filter to only include image files
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"}
        valid_images = []
        skipped_files = []
        
        for file_path in all_files:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in image_extensions:
                valid_images.append(file_path)
            else:
                skipped_files.append(file_path)
                
        if skipped_files:
            logger.info(f"Skipped {len(skipped_files)} non-image files: {skipped_files[:5]}{'...' if len(skipped_files) > 5 else ''}")
        
        logger.info(f"Processing {len(valid_images)} valid image files")
        
        # Find which files need to be added
        new_files = [f for f in valid_images if f not in existing_paths]
        logger.info(f"Found {len(new_files)} new images to add to database")
        
        # Add new files to database
        added_count = 0
        added_files = []
        
        for file_path in new_files:
            # Generate public URL - handle uniform bucket-level access
            blob = gcs_client.bucket.blob(file_path)
            # Check if uniform bucket-level access is enabled
            try:
                blob.make_public()
            except Exception as e:
                logger.warning(f"Cannot make blob public, likely uniform bucket-level access is enabled: {e}")
                # For uniform bucket-level access, we use the pre-configured public URL format
                # No need to set individual ACLs
            
            # Extract filename as title
            filename = os.path.basename(file_path)
            title = os.path.splitext(filename)[0].replace("_", " ").title()
            
            # Create URL for the file
            url = f"https://storage.googleapis.com/{settings.GCS_BUCKET}/{file_path}"
            
            # Get mimetype based on extension
            ext = os.path.splitext(filename)[1].lower()
            mimetype = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".tiff": "image/tiff",
                ".bmp": "image/bmp"
            }.get(ext, "application/octet-stream")
            
            # Add to database
            photo = models.Photo(
                title=title,
                description=f"Imported from GCS: {file_path}",
                url=url,
                gcs_path=file_path,
                mimetype=mimetype,
                is_public=True,
                folder_id=1,  # Default folder
            )
            db.add(photo)
            added_count += 1
            added_files.append(file_path)
        
        db.commit()
        db.close()
        
        logger.info(f"Successfully added {added_count} new photos to database")
        
        # Return detailed results
        return {
            "message": f"Successfully indexed {len(valid_images)} images from GCS. Added {added_count} new photos to database.",
            "details": {
                "total_files_found": len(all_files),
                "valid_images": len(valid_images),
                "new_images_added": added_count,
                "skipped_non_image_files": len(skipped_files),
                "already_in_database": len(valid_images) - len(new_files),
                "added_files": added_files[:10] + ['...'] if len(added_files) > 10 else added_files
            }
        }
    except Exception as e:
        if 'db' in locals() and db:
            db.close()
            
        logger.error(f"Error reindexing GCS bucket: {str(e)}", exc_info=True)
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reindexing GCS bucket: {str(e)}"
        )

# Batch Upload Endpoint
@app.post("/api/upload")
async def batch_upload(
    background_tasks: BackgroundTasks,
    folder: str = Form(...),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload multiple images to a folder"""
    logger.info(f"Batch upload request received for folder '{folder}' with {len(images)} images")
    
    if not gcs_client or not gcs_client.available:
        logger.error("GCS client is not available for batch upload")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service is not available"
        )
    
    # Get or create folder
    db_folder = db.query(models.Folder).filter(models.Folder.name == folder).first()
    if not db_folder:
        logger.info(f"Creating new folder: {folder}")
        db_folder = models.Folder(name=folder, description=f"Folder: {folder}")
        db.add(db_folder)
        db.commit()
        db.refresh(db_folder)
    
    uploaded_count = 0
    errors = []
    
    # Process each image
    for image in images:
        try:
            # Create a temporary file for this image
            filename = os.path.basename(image.filename)
            temp_path = os.path.join("uploads", filename)
            os.makedirs("uploads", exist_ok=True)
            
            # Save the file locally first
            with open(temp_path, "wb") as f:
                content = await image.read()
                f.write(content)
            
            # Upload to GCS
            blob_path = f"photos/{filename}"
            try:
                with open(temp_path, "rb") as f:
                    # Add metadata
                    metadata = {
                        "original_filename": filename,
                        "folder": folder,
                        "upload_time": datetime.datetime.now().isoformat()
                    }
                    
                    # Upload file to GCS
                    file_url = gcs_client.upload_file(
                        f,
                        blob_path,
                        content_type=image.content_type,
                        metadata=metadata
                    )
                    
                # Create photo record
                photo_data = {
                    "filename": filename,
                    "title": os.path.splitext(filename)[0].replace("_", " ").title(),
                    "description": f"Uploaded to folder: {folder}",
                    "url": file_url,
                    "gcs_path": blob_path,
                    "storage_path": blob_path,  # Also set storage_path field
                    "mimetype": image.content_type,
                    "file_size": len(content),  # Set the file size
                    "is_public": True,
                    "folder_id": db_folder.id,
                    "owner_id": 1  # Default admin owner
                }
                
                db_photo = models.Photo(**photo_data)
                db.add(db_photo)
                
                # Schedule temp file cleanup
                background_tasks.add_task(lambda p: os.unlink(p) if os.path.exists(p) else None, temp_path)
                
                uploaded_count += 1
                logger.info(f"Successfully uploaded {filename} to {blob_path}")
                
            except Exception as e:
                # Log error and continue with next image
                error_msg = f"Failed to upload {filename}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Try to clean up the temp file
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
                
        except Exception as e:
            # Log error and continue with next image
            error_msg = f"Error processing {image.filename}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Commit successful uploads
    db.commit()
    
    # Prepare response
    response = {
        "uploaded": uploaded_count,
        "total": len(images),
        "folder": folder,
        "folder_id": db_folder.id
    }
    
    if errors:
        response["errors"] = errors
        if uploaded_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "All uploads failed", "errors": errors}
            )
    
    return response

# Include routers if they were imported successfully
for name, router in ROUTERS.items():
    app.include_router(router)
    logger.info(f"Included router: {name}")

# Add a route to check available endpoints
@app.get("/api/endpoints")
async def list_endpoints():
    """List all available API endpoints."""
    endpoints = []
    for route in app.routes:
        if hasattr(route, "methods"):
            endpoints.append({
                "path": route.path,
                "methods": sorted(list(route.methods)),
                "name": getattr(route, "name", ""),
                "tags": getattr(route, "tags", [])
            })
    return {"endpoints": endpoints}

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
