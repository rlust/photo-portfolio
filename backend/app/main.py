import sys
import os
import logging
import datetime
import json
import time
import uuid
from pathlib import Path

# Configure logging before any imports
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Starting application initialization process")

# Create the FastAPI app first to ensure it can respond to health checks
from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Photo Portfolio API", version="1.0.0")

# Basic routes that must always work
@app.get("/")
def root():
    return {"message": "Photo Portfolio API is running"}

@app.get("/api/health")
def health_check():
    """Basic health check endpoint for Cloud Run"""
    health_data = {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "production"),
        "services": {
            "api": "up"
        }
    }
    return health_data

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the static directory
os.makedirs("static", exist_ok=True)

# Flag for tracking imported features
HAS_DB = False
HAS_GCS = False
gcs_client = None
GCSClient = None

# Try to load additional features but don't fail the app if they're not available
try:
    # Import advanced dependencies that might not be available in all environments
    import sqlalchemy
    from fastapi import Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from sqlalchemy.orm import Session
    from typing import List, Optional, Dict, Any
    
    # Try to import database modules but handle potential failures gracefully
    try:
        from .config import Base, get_db, settings, engine
        from .database import init_db, reset_db
        from . import models, schemas
        logger.info("Successfully imported database modules")
        HAS_DB = True
    except Exception as db_error:
        logger.warning(f"Database modules not available: {db_error}")
        
    # Try to import GCS modules but handle potential failures gracefully
    try:
        from .utils.gcs import GCSClient as GCSClientClass
        GCSClient = GCSClientClass
        logger.info("Successfully imported GCS client class")
        HAS_GCS = True
    except Exception as gcs_error:
        logger.warning(f"GCS modules not available: {gcs_error}")
        
    # Try to import the routers but handle potential failures gracefully
    ROUTERS = {}
    try:
        from .routes import folders
        ROUTERS['folders'] = folders.router
        logger.info("Successfully imported folders router")
    except Exception as folder_error:
        logger.warning(f"Folders router not available: {folder_error}")
        
    # Only try to import photos router if GCS is available
    if HAS_GCS:
        try:
            from .routes import photos
            ROUTERS['photos'] = photos.router
            logger.info("Successfully imported photos router")
        except Exception as photos_error:
            logger.warning(f"Photos router not available: {photos_error}")
            
except Exception as e:
    logger.warning(f"Non-critical import error: {e}")
    logger.info("Application will start with limited functionality")
except ImportError as e:
    logger.critical(f"Critical import error: {e}")
    raise

    # Import dependencies with improved error handling
    ROUTERS = {}
    gcs_client = None
    GCSClient = None  # Will be set later if import succeeds

    # First import the routes that don't depend on GCS
    try:
        from .routes import folders
        ROUTERS['folders'] = folders.router
        logger.info("Successfully imported folders router")
    except Exception as e:
        logger.warning(f"Failed to import folders router: {e}")
        
    # Then try to import GCS class - but don't initialize yet
    try:
        from .utils.gcs import GCSClient as GCSClientClass
        GCSClient = GCSClientClass  # Store the class for lazy initialization
        logger.info("Successfully imported GCS client class - will initialize lazily")
        
        # Only import photos router if GCS client class is available
        try:
            from .routes import photos
            ROUTERS['photos'] = photos.router
            logger.info("Successfully imported photos router")
        except Exception as photos_error:
            logger.warning(f"Failed to import photos router: {photos_error}")
            
    except ImportError as e:
        logger.warning(f"GCS dependencies not available: {e}")
        # Continue without GCS client
    except Exception as e:
        logger.error(f"Error during GCS setup: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Continue without GCS client


# Initialize FastAPI app
app = FastAPI(
    title="Photo Portfolio API",
    description="API for managing photo portfolios",
    version="1.0.0",
    # Disable automatic redirect when trailing slash is missing
    redirect_slashes=False
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Range"],
    max_age=600  # Cache preflight requests for 10 minutes
)

# Mount static files directory for uploads and serving
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add a route to get static file URLs that work with our deployment
@app.get("/api/static-url/{path:path}", tags=["utils"])
async def get_static_url(path: str):
    """Convert a local static path to a publicly accessible URL"""
    # For Cloud Run deployments, this ensures static files are accessible
    if path.startswith("/static/"):
        path = path[8:]  # Remove leading /static/
    elif path.startswith("static/"):
        path = path[7:]  # Remove leading static/
        
    # Return the full URL to the static resource
    service_url = os.environ.get("SERVICE_URL", "https://photoportfolio-backend-er4l5fctxq-uc.a.run.app")
    return {"url": f"{service_url}/static/{path}"}

# Add a reindex endpoint to help with showing local images in gallery
@app.get("/api/reindex-gcs", tags=["utils"])
async def reindex_gcs(db: Session = Depends(get_db)):
    """Reindex all photos in the database, updating their URLs.
    This is useful when switching between GCS and local storage."""
    try:
        # Get all photos
        photos = db.query(models.Photo).all()
        updated = 0
        
        for photo in photos:
            # Check if it's a local file
            if photo.gcs_path and photo.gcs_path.startswith("local:"):
                # Extract the path and update the URL to use our backend service
                local_path = photo.gcs_path.replace("local:", "")
                service_url = os.environ.get("SERVICE_URL", "https://photoportfolio-backend-er4l5fctxq-uc.a.run.app")
                photo.url = f"{service_url}/static{local_path}"
                updated += 1
                
        # Commit changes
        db.commit()
        
        return {"message": f"Reindexed {updated} photos", "total": len(photos)}            
    except Exception as e:
        logger.error(f"Error reindexing GCS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reindexing: {str(e)}"
        )

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
@app.post("/api/upload/")
async def batch_upload(
    background_tasks: BackgroundTasks,
    folder: str = Form(...),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload multiple images to a folder"""
    import mimetypes
    import uuid
    import pathlib
    import time
    
    logger.info(f"Batch upload request received for folder '{folder}' with {len(images)} images")
    start_time = time.time()
    
    # Create folder in database if it doesn't exist
    try:
        # First try to get the folder by name
        db_folder = db.query(models.Folder).filter(models.Folder.name == folder).first()
        
        if not db_folder:
            logger.info(f"Creating new folder in database: {folder}")
            # Create a new folder with the default admin user (ID 1)
            new_folder = models.Folder(
                name=folder,
                description=f"Uploaded photos for {folder}",
                is_public=True,
                owner_id=1  # Using default admin user ID
            )
            db.add(new_folder)
            db.flush()  # Get the ID without committing transaction
            db_folder = new_folder
    except Exception as e:
        logger.error(f"Error creating/getting folder: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create folder: {str(e)}"
        )
    
    # Use the globally defined GCSClient class for lazy initialization
    # This approach makes the backend more resilient to startup failures
    global GCSClient, gcs_client
    
    # Check if we already have a global gcs_client initialized
    if gcs_client is None and GCSClient is not None:
        try:
            logger.info("Lazily initializing GCS client for batch upload...")
            gcs_client = GCSClient()
            logger.info(f"GCS client initialized: {gcs_client.is_initialized}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {str(e)}")
            # We'll continue with a non-functional client that will use local storage
            logger.warning("Using local storage fallback for file uploads due to GCS initialization error")
    elif GCSClient is None:
        logger.error("GCSClient class not available - uploads will fail")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File upload service temporarily unavailable"
        )
    
    # If gcs_client is still None at this point, we'll create a dummy client
    # that will default to local storage
    if gcs_client is None:
        try:
            logger.warning("Creating fallback GCS client that will use local storage")
            from .utils.gcs import GCSClient as LocalGCSClient
            gcs_client = LocalGCSClient()
        except Exception as local_error:
            logger.error(f"Could not create local fallback: {local_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File upload service temporarily unavailable"
            )
    
    # Process each image
    uploaded_files = []
    errors = []
    uploaded_count = 0
    
    for image in images:
        try:
            # Get file info
            content = await image.read()
            filename = image.filename
            ext = pathlib.Path(filename).suffix.lower()
            
            # Generate a unique filename
            unique_name = f"{uuid.uuid4()}{ext}"
            gcs_path = f"{folder}/{unique_name}"
            
            # Get content type
            content_type = image.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            
            logger.info(f"Uploading file {filename} ({len(content)} bytes) to {gcs_path}")
            
            # Create file-like object from bytes
            from io import BytesIO
            buffer = BytesIO(content)
            
            # Upload file to GCS
            metadata = {
                "original_filename": filename,
                "uploaded_at": datetime.datetime.now().isoformat(),
                "content_type": content_type,
                "folder": folder
            }
            
            url = gcs_client.upload_file(
                buffer, gcs_path, content_type=content_type, metadata=metadata
            )
            
            # Handle local storage URLs differently
            # If URL is prefixed with 'local:', it's a local file
            original_url = url
            if url.startswith("local:"):
                # Extract the path and update the URL to use our backend service
                local_path = url.replace("local:", "")
                service_url = os.environ.get("SERVICE_URL", "https://photoportfolio-backend-er4l5fctxq-uc.a.run.app")
                url = f"{service_url}{local_path}"
                logger.info(f"Local file, using URL: {url}")
            
            logger.info(f"Uploaded file to {url}")
            
            # Create photo record in database
            photo_data = schemas.PhotoCreate(
                title=filename,
                filename=unique_name,
                original_filename=filename,
                description="",
                url=url,  # Public URL to access the file
                gcs_path=original_url,  # Store 'local:' prefix if it's a local file
                mimetype=content_type,
                size=len(content),
                folder_id=db_folder.id
            )
            
            db_photo = crud.create_photo(db=db, photo=photo_data)
            logger.info(f"Created photo record with ID {db_photo.id}")
            
            uploaded_files.append({
                "name": filename,
                "url": url,
                "id": db_photo.id,
                "size": len(content),
                "type": content_type
            })
            
            uploaded_count += 1
            
        except Exception as e:
            # Log error and continue with next image
            error_msg = f"Failed to process {image.filename}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Commit successful uploads if using database
    if db and engine is not None:
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Error committing to database: {str(e)}")
    
    # Calculate duration
    duration = time.time() - start_time
    logger.info(f"Batch upload completed in {duration:.2f}s")
    
    # Prepare response with appropriate status code
    if uploaded_count == 0 and errors:
        # All uploads failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "All uploads failed", "errors": errors}
        )
    
    # Return success response
    return {
        "message": f"Batch upload completed. {uploaded_count} files processed.",
        "uploaded_files": uploaded_files,
        "uploaded_count": uploaded_count,
        "total": len(images),
        "folder": folder,
        "errors": errors if errors else None,
        "duration": f"{duration:.2f}s"
    }

# Make database connection more resilient for startup
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    if engine is None:
        # Return a helpful response if database is not configured
        if request.url.path.startswith("/api/upload"):
            # For upload endpoint, continue even without DB
            pass
        elif request.url.path == "/api/health" or request.url.path == "/":
            # Allow health checks
            pass
        else:
            # For other endpoints, return friendly message
            return JSONResponse(
                status_code=503,
                content={"detail": "Database service is temporarily unavailable. Only uploads and static file serving are available."}
            )
    
    response = await call_next(request)
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
