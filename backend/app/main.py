import sys
try:
    import os
    import logging
    import sqlalchemy
    from fastapi import FastAPI, Depends, status, HTTPException, BackgroundTasks
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
    version="1.0.0"
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
    
    # Check storage connection if GCS is configured
    if settings.GCS_BUCKET:
        try:
            from google.cloud import storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(settings.GCS_BUCKET)
            # Just check if we can list a small number of blobs to verify access
            next(bucket.list_blobs(max_results=1), None)
            response["services"]["storage"] = True
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
        # Get database session
        db = next(get_db())
        
        # Get existing photos from DB for comparison
        existing_photos = {photo.gcs_uri: photo for photo in db.query(models.Photo).all()}
        logger.info(f"Found {len(existing_photos)} existing photos in database")
        
        # List all files in the GCS bucket
        all_files = gcs_client.list_files()
        image_files = [f for f in all_files if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))]
        logger.info(f"Found {len(image_files)} image files in GCS bucket")
        
        # Files to add to database
        new_files = []
        for file_path in image_files:
            gcs_uri = f"gs://{gcs_client.bucket_name}/{file_path}"
            if gcs_uri not in existing_photos:
                new_files.append(file_path)
        
        # Create a default folder if none exists
        default_folder = db.query(models.Folder).filter(models.Folder.name == "Default").first()
        if not default_folder:
            default_folder = models.Folder(name="Default", description="Default folder for all photos")
            db.add(default_folder)
            db.commit()
            db.refresh(default_folder)
            logger.info("Created default folder for photos")
        
        # Add new files to database
        added_count = 0
        for file_path in new_files:
            # Generate public URL
            blob = gcs_client.bucket.blob(file_path)
            blob.make_public()
            
            # Extract filename as title
            filename = os.path.basename(file_path)
            title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
            
            # Create photo record
            photo = models.Photo(
                title=title,
                description=f"Imported from GCS: {file_path}",
                folder_id=default_folder.id,
                gcs_uri=f"gs://{gcs_client.bucket_name}/{file_path}",
                url=blob.public_url,
                width=0,  # Could be populated later with image processing
                height=0  # Could be populated later with image processing
            )
            db.add(photo)
            added_count += 1
            
            # Commit in batches to avoid timeouts
            if added_count % 20 == 0:
                db.commit()
                logger.info(f"Added {added_count} photos so far")
        
        # Final commit for any remaining photos
        if added_count % 20 != 0:
            db.commit()
        
        logger.info(f"Successfully added {added_count} new photos to database")
        return {"message": f"Successfully indexed {len(image_files)} images from GCS. Added {added_count} new photos to database."}
    
    except Exception as e:
        logger.error(f"Error during GCS reindexing: {e}")
        # Rollback in case of error
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reindexing GCS bucket: {str(e)}"
        )

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
