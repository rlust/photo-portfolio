from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel
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
logger.info("Starting simplified application")

# Define request models
class DeleteImageRequest(BaseModel):
    folder: str
    filename: str

# Create the FastAPI app
app = FastAPI(title="Photo Portfolio API - Simplified", version="1.0.0")

# Add CORS middleware - allowing all origins temporarily to debug CORS issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Content-Length", "Content-Disposition"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Create necessary directories
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Basic routes
@app.get("/")
def root():
    return {"message": "Photo Portfolio API is running"}

@app.get("/api/health")
def health_check():
    """Basic health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "production")
    }

# Simple endpoint to list folders - supporting both with and without trailing slash
@app.get("/api/folders")
@app.get("/api/folders/")
def list_folders():
    """List all available folders"""
    try:
        # For debugging purposes, add a log entry when this endpoint is hit
        logger.info(f"FOLDERS API: Request received to list folders")
        
        # Create the folder data structure
        folders_data = {
            "Landscapes": [],
            "Portraits": [],
            "Events": [],
            "Nature": [],
            "Travel": []
        }
        
        # Return the folders in the format needed by the frontend
        return folders_data
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
            service_url = os.environ.get("SERVICE_URL", "http://localhost:8080")
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

# Add an endpoint to delete an image
@app.post("/api/delete-image/")
async def delete_image(request: DeleteImageRequest):
    """Delete an image from a folder"""
    logger.info(f"Delete image request for {request.filename} from folder {request.folder}")
    
    try:
        # Construct the path to the image file
        image_path = os.path.join("uploads", request.filename)
        
        if os.path.exists(image_path):
            # Remove the file
            os.remove(image_path)
            logger.info(f"Deleted file: {image_path}")
            return {"success": True, "message": f"Image {request.filename} deleted successfully"}
        else:
            logger.warning(f"File not found: {image_path}")
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"Image {request.filename} not found"}
            )
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error deleting image: {str(e)}"}
        )

# Add an endpoint to list uploaded files
@app.get("/api/files/")
async def list_files():
    """List all uploaded files"""
    try:
        uploads_dir = Path("uploads")
        files = []
        
        for file_path in uploads_dir.glob("*"):
            if file_path.is_file():
                service_url = os.environ.get("SERVICE_URL", "http://localhost:8080")
                file_url = f"{service_url}/uploads/{file_path.name}"
                
                files.append({
                    "filename": file_path.name,
                    "url": file_url,
                    "size": file_path.stat().st_size,
                    "modified": datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
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
