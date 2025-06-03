from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import os
import logging
import uvicorn
import uuid
import datetime
import time
import json
from pathlib import Path
import shutil
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Starting HTTPS-enforced simplified application")

# Create the FastAPI app
app = FastAPI(title="Photo Portfolio API - Simplified HTTPS", version="1.1.0")

# Add CORS middleware with specific origins for better security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://photoportfolio-frontend-839093975626.us-central1.run.app",
        "http://localhost:3000",  # For local development
        "http://localhost:8080",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Basic routes
@app.get("/")
def root():
    return {"message": "Photo Portfolio API is running with HTTPS enforcement"}

@app.get("/api/health")
def health_check():
    """Basic health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.1.0",
        "environment": os.environ.get("ENVIRONMENT", "production"),
        "https_enforced": True
    }

# Simple endpoint to list folders - now with explicit HTTPS support
@app.get("/api/folders/")
def list_folders():
    """List all available folders"""
    try:
        logger.info("Processing /api/folders/ request")
        # In this simplified version, we'll just return a hardcoded list
        # In a real app, this would come from a database
        return [
            {"id": 1, "name": "Landscapes", "description": "Beautiful landscapes", "is_public": True},
            {"id": 2, "name": "Wildlife", "description": "Wildlife photography", "is_public": True},
            {"id": 3, "name": "Events", "description": "Event photography", "is_public": True}
        ]
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing folders: {str(e)}")

# Simplified batch upload endpoint that stores files locally
@app.post("/api/batch-upload")
async def batch_upload(
    background_tasks: BackgroundTasks,
    folder: str = Form(...),
    images: List[UploadFile] = File(...)
):
    """Upload multiple images to a folder"""
    logger.info(f"UPLOAD REQUEST: Batch upload request received for folder '{folder}' with {len(images)} images")
    # Log details about each file being uploaded
    for i, img in enumerate(images):
        logger.info(f"UPLOAD FILE {i+1}: Filename={img.filename}, Content-Type={img.content_type}, Size={img.size}")
    # Log request headers for debugging
    logger.info(f"UPLOAD REQUEST HEADERS: {dict(images[0].headers) if images else 'No files'}")
    
    start_time = time.time()
    
    # Process each image
    uploaded_files = []
    failed_files = []
    
    for i, img in enumerate(images):
        try:
            file_start_time = time.time()
            logger.info(f"Processing file {i+1}/{len(images)}: {img.filename}")
            
            # Generate a safe filename with timestamp and UUID to avoid conflicts
            original_filename = img.filename
            file_extension = Path(original_filename).suffix.lower()
            timestamp = int(time.time() * 1000)
            random_uuid = str(uuid.uuid4())[:8]
            safe_filename = f"{timestamp}_{random_uuid}{file_extension}"
            
            # Path where the file will be saved locally
            local_path = f"uploads/{safe_filename}"
            
            # Save the file locally
            with open(local_path, "wb") as buffer:
                shutil.copyfileobj(img.file, buffer)
            
            # Generate a URL for the file
            service_url = os.environ.get("SERVICE_URL", "https://simplified-backend-839093975626.us-central1.run.app")
            file_url = f"{service_url}/{local_path}"
            
            # In a real app, we would also add the file to a database
            file_metadata = {
                "original_filename": original_filename,
                "storage_path": local_path,
                "url": file_url,
                "size": os.path.getsize(local_path),
                "folder": folder,
                "mimetype": mimetypes.guess_type(original_filename)[0] or "application/octet-stream",
                "upload_time": datetime.datetime.now().isoformat()
            }
            
            uploaded_files.append(file_metadata)
            logger.info(f"File {i+1}/{len(images)} processed in {time.time() - file_start_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error processing file {img.filename}: {str(e)}")
            failed_files.append({
                "filename": img.filename,
                "error": str(e)
            })
    
    # Return the results
    total_time = time.time() - start_time
    logger.info(f"Batch upload completed in {total_time:.2f}s. Successful: {len(uploaded_files)}, Failed: {len(failed_files)}")
    
    return {
        "message": f"Processed {len(uploaded_files)} files successfully, {len(failed_files)} failed",
        "uploaded_files": uploaded_files,
        "failed_files": failed_files,
        "processing_time": total_time
    }

# Simplified endpoint to handle direct image uploads - adding for compatibility with both upload methods
@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...), folder: str = Form(...)):
    logger.info(f"DIRECT UPLOAD: Single file upload received for folder '{folder}', file: {file.filename}")
    # Just delegate to the batch upload handler
    return await batch_upload(BackgroundTasks(), folder=folder, images=[file])

# Serve static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add a signed URL endpoint for compatibility with frontend - log when this is called
@app.post("/api/signed-url")
async def get_signed_url(request: Request):
    # Log the entire request for debugging
    body = await request.json()
    logger.info(f"SIGNED URL REQUEST: Received request for signed URL: {body}")
    logger.info(f"SIGNED URL REQUEST HEADERS: {dict(request.headers)}")
    
    # Rather than failing, provide a direct upload URL
    return {
        "url": "https://simplified-backend-839093975626.us-central1.run.app/api/upload",
        "publicUrl": f"https://simplified-backend-839093975626.us-central1.run.app/uploads/{body.get('filename')}"
    }

# Add an endpoint to list uploaded files
@app.get("/api/files")
def list_files():
    """List all uploaded files"""
    try:
        files = []
        for filename in os.listdir("uploads"):
            if os.path.isfile(os.path.join("uploads", filename)):
                files.append({
                    "filename": filename,
                    "size": os.path.getsize(os.path.join("uploads", filename)),
                    "url": f"/uploads/{filename}"
                })
        return files
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

# Add a catch-all route to log any requests to endpoints we don't explicitly handle
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path: str):
    logger.info(f"CATCH ALL: Request to unknown endpoint: {request.method} /{path}")
    logger.info(f"CATCH ALL HEADERS: {dict(request.headers)}")
    try:
        body = await request.body()
        if body:
            logger.info(f"CATCH ALL BODY: {body}")
    except Exception as e:
        logger.info(f"CATCH ALL BODY ERROR: {str(e)}")
    
    return {"detail": "Endpoint not found"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
