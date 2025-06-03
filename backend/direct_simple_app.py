from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
import os
import uvicorn
import datetime
import requests
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Starting direct simplified application")

# Create the FastAPI app
app = FastAPI(title="Direct Simple API", version="1.0.0")

# Add CORS middleware with permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Content-Length"],
)

@app.get("/")
def root():
    return {"message": "Direct Simple API is running"}

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/folders")
@app.get("/api/folders/")
def list_folders():
    """List folders in the format expected by the frontend"""
    logger.info("Request received to list folders")
    
    # Return an empty folders structure that matches what the frontend expects
    folders_data = {
        "Landscapes": [],
        "Portraits": [],
        "Events": [],
        "Nature": [],
        "Travel": []
    }
    
    return folders_data

@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    """Handle preflight OPTIONS requests for all routes"""
    logger.info(f"Handling OPTIONS request for /{rest_of_path}")
    return {}

from pydantic import BaseModel

# Define the target backend for image proxying
TARGET_IMAGE_BACKEND = "https://simplified-backend-839093975626.us-central1.run.app"

# Define request models
class DeleteImageRequest(BaseModel):
    folder: str
    filename: str
    
class AnnotateImageRequest(BaseModel):
    folder: str
    filename: str

@app.get("/uploads/{filename:path}")
async def proxy_image(filename: str):
    """Proxy image requests to the simplified backend"""
    target_url = f"{TARGET_IMAGE_BACKEND}/uploads/{filename}"
    logger.info(f"Proxying image request to: {target_url}")
    
    try:
        # Stream the image from the simplified backend
        response = requests.get(target_url, stream=True)
        
        if response.status_code == 200:
            # Create a streaming response with the same headers
            headers = {key: value for key, value in response.headers.items()
                      if key.lower() not in ["transfer-encoding", "content-encoding", "content-length"]}
            
            # Add CORS headers
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            
            # Return the streamed response
            return StreamingResponse(
                response.iter_content(chunk_size=8192),
                status_code=response.status_code,
                headers=headers,
                media_type=response.headers.get("content-type", "application/octet-stream")
            )
        else:
            # Return the error from the backend
            logger.error(f"Error proxying image: {response.status_code}")
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={"Access-Control-Allow-Origin": "*"}
            )
    except Exception as e:
        logger.error(f"Error proxying image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error proxying image: {str(e)}")

@app.post("/api/annotate-image/")
async def annotate_image(request: AnnotateImageRequest):
    """Annotate an image using the simplified backend"""
    logger.info(f"Annotate image request: {request}")
    
    try:
        # Forward the annotation request to the simplified backend
        target_url = f"{TARGET_IMAGE_BACKEND}/api/annotate-image/"
        
        # Make the request to the simplified backend
        response = requests.post(
            target_url,
            json={"folder": request.folder, "filename": request.filename},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully annotated image {request.filename} from folder {request.folder}")
            return response.json()
        else:
            logger.error(f"Failed to annotate image: {response.status_code} - {response.text}")
            return {"success": False, "message": f"Failed to annotate image: {response.text}"}
    except Exception as e:
        logger.error(f"Error annotating image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error annotating image: {str(e)}")

@app.post("/api/delete-image/")
async def delete_image(request: DeleteImageRequest):
    """Delete an image from the simplified backend"""
    logger.info(f"Delete image request: {request}")
    
    try:
        # Forward the deletion request to the simplified backend
        target_url = f"{TARGET_IMAGE_BACKEND}/api/delete-image/"
        
        # Make the request to the simplified backend
        response = requests.post(
            target_url,
            json={"folder": request.folder, "filename": request.filename},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully deleted image {request.filename} from folder {request.folder}")
            return {"success": True, "message": "Image deleted successfully"}
        else:
            logger.error(f"Failed to delete image: {response.status_code} - {response.text}")
            return {"success": False, "message": f"Failed to delete image: {response.text}"}
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting image: {str(e)}")

@app.get("/{path:path}")
async def catch_all(request: Request, path: str):
    """Catch-all route for debugging"""
    logger.info(f"Request to: {request.method} /{path}")
    return {"message": f"Endpoint /{path} not implemented in direct simple API"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
