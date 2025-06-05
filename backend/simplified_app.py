from fastapi import FastAPI, File, UploadFile, Form, Request, Response, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import FastAPI, Query, Body, HTTPException, Request
import io
import time
import hashlib
import datetime
import traceback
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import requests
# Google Cloud Vision API integration
from google.cloud import vision
from google.cloud import storage
import io
import base64
import os
import logging
import sys
# Import CLIP tagger
from clip_tagger import tag_image_with_clip

# Configure logging for better visibility in Cloud Run
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
import uvicorn
import uuid
import datetime
import time
import json
from pathlib import Path
import shutil
import mimetypes
import numpy as np

# For semantic search - use sentence-transformers if available, fall back to simple text matching
try:
    from sentence_transformers import SentenceTransformer
    _semantic_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    has_semantic_search = True
except ImportError:
    has_semantic_search = False
    logging.warning("sentence-transformers not installed. Falling back to basic text matching for search.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Starting simplified application")

# Define request models
class DeleteImageRequest(BaseModel):
    folder: str
    filename: str

class FolderRequest(BaseModel):
    folder: str

class AnnotateImageRequest(BaseModel):
    folder: str
    filename: str
    
class AnnotationResponse(BaseModel):
    description: Optional[str] = None
    location_tag: Optional[str] = None
    tags: List[str] = []

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

# Global variables for caching and configuration
GCS_BUCKET = os.environ.get("GCS_BUCKET", "photoportfolio-uploads")
storage_client = None
image_metadata_cache = []
last_cache_update = None

# Helper function to update the image metadata cache for search
def update_image_metadata_cache():
    """Update the global cache of image metadata for search functionality"""
    global image_metadata_cache, last_cache_update
    
    # Only update cache if it's empty or older than 10 minutes
    current_time = time.time()
    if last_cache_update and (current_time - last_cache_update < 600) and image_metadata_cache:
        return
    
    try:
        # Get bucket info
        bucket_name = GCS_BUCKET  # Use the global variable
        service_url = os.environ.get("SERVICE_URL", "https://simplified-backend-ymcejj57ga-uc.a.run.app")
        
        # Initialize storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Clear existing cache
        image_metadata_cache.clear()
        
        # List all blobs in bucket and organize by folder
        blobs = list(bucket.list_blobs())
        
        for blob in blobs:
            # Skip system files or empty folder markers
            if blob.name.startswith('.') or blob.name.endswith('/') or '/.tmp/' in blob.name:
                continue
                
            # Parse folder and filename
            path_parts = blob.name.split('/')
            if len(path_parts) < 2:
                continue  # Skip files not in folders
                
            folder = path_parts[0]
            filename = path_parts[-1]
            
            # Generate public URL
            url = f"{service_url}/static/{blob.name}"
            
            # Get content type
            mimetype = blob.content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            
            # Get upload time
            uploaded_at = blob.time_created.isoformat() if blob.time_created else None
            
            # Add to cache
            image_metadata_cache.append({
                'folder': folder,
                'name': filename,
                'url': url,
                'mimetype': mimetype,
                'uploaded_at': uploaded_at,
                'tags': [],  # Tags would be populated from metadata if available
                'location': None,  # Location would be populated from metadata
            })
        
        # Update timestamp
        last_cache_update = current_time
        logger.info(f"Updated search metadata cache with {len(image_metadata_cache)} items")
        
    except Exception as e:
        logger.error(f"Failed to update image metadata cache: {str(e)}")
        # Continue with existing cache if there's an error


# Simple endpoint to list folders - supporting both with and without trailing slash
@app.get("/api/folders")
@app.get("/api/folders/")
def list_folders():
    """List all available folders and their images from GCS bucket"""
    try:
        # For debugging purposes, add a log entry when this endpoint is hit
        logger.info(f"FOLDERS API: Request received to list folders")
        
        # Use the global GCS bucket name
        bucket_name = GCS_BUCKET
        
        # Update to use current service URLs
        primary_service_url = "https://simplified-backend-ymcejj57ga-uc.a.run.app"
        fallback_service_url = "https://photoportfolio-backend-er4l5fctxq-uc.a.run.app"
        
        # Use the primary URL as default, with environment variable as override
        service_url = os.environ.get("SERVICE_URL", primary_service_url)
        
        # Update search cache at the same time
        update_image_metadata_cache()
        
        # Initialize folders data
        folders_data = {}
        
        # Get global storage client
        global storage_client
        
        # If storage client isn't initialized, try to initialize it now
        if not storage_client:
            logger.info("Storage client not initialized, attempting to initialize it now")
            try:
                storage_client = storage.Client()
                logger.info("Successfully initialized storage client")
            except Exception as init_error:
                logger.error(f"Failed to initialize storage client: {str(init_error)}")
                # Fall back to default empty folder structure
                return {
                    "Landscapes": [],
                    "Portraits": [],
                    "Events": [],
                    "Nature": [],
                    "Travel": []
                }
        
        # Get all blobs in the bucket with folders/ prefix
        logger.info(f"Listing blobs from bucket: {bucket_name} with prefix 'folders/'")
        blobs = list(storage_client.list_blobs(bucket_name, prefix="folders/"))
        logger.info(f"Found {len(blobs)} blobs in the bucket")
        
        # Extract folder names and organize images by folder
        for blob in blobs:
            # Skip the folders/ prefix itself
            if blob.name == "folders/":
                continue
                
            # Extract folder name and filename from path
            path_parts = blob.name.split('/')
            if len(path_parts) > 2 and path_parts[0] == "folders":
                folder_name = path_parts[1]
                filename = path_parts[2]
                
                # Skip if this is a folder reference and not an actual file
                if not filename or filename.endswith('/'):
                    continue
                
                # Create folder if it doesn't exist yet
                if folder_name not in folders_data:
                    folders_data[folder_name] = []
                
                # Create public URL for the image
                url = f"{service_url}/static/{folder_name}/{filename}"
                storage_path = blob.name
                gcs_url = f"https://storage.googleapis.com/{bucket_name}/{storage_path}"
                
                # Add image metadata
                image_info = {
                    "name": filename,
                    "url": url,
                    "storage_path": storage_path,
                    "gcs_url": gcs_url,
                    "size": blob.size,
                    "updated": blob.updated.isoformat() if blob.updated else None
                }
                
                folders_data[folder_name].append(image_info)
        
        # If we found no folders, fall back to default structure
        if not folders_data:
            logger.warning("No folders found in GCS bucket, using default structure")
            folders_data = {
                "Landscapes": [],
                "Portraits": [],
                "Events": [],
                "Nature": [],
                "Travel": []
            }
        
        # Log results
        logger.info(f"Returning folders: {list(folders_data.keys())}")
        for folder, images in folders_data.items():
            logger.info(f"Folder '{folder}' has {len(images)} images")
        
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

# Serve static files - these are fallbacks for local development
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add a GCS proxy endpoint for serving images directly from Google Cloud Storage
@app.get("/gcs-proxy/{folder}/{filename}")
async def gcs_proxy(folder: str, filename: str, request: Request):
    """Proxy endpoint to serve files directly from GCS bucket with improved error handling and caching"""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    request_id = f"{folder}-{filename}-{int(time.time())}"
    
    logger.info(f"[{request_id}] GCS proxy request from {client_ip} ({user_agent}): folder={folder}, filename={filename}")
    
    try:
        # Initialize storage client if needed
        global storage_client
        if not storage_client:
            logger.info(f"[{request_id}] Initializing new storage client")
            storage_client = storage.Client()
        
        # Try multiple possible paths in GCS
        possible_paths = [
            f"folders/{folder}/{filename}",  # Standard path
            f"{folder}/{filename}",          # Direct folder/file path
            f"uploads/{filename}",           # From uploads directory
            f"static/{filename}"             # From static directory
        ]
        
        content = None
        content_type = None
        object_path = None
        bucket = storage_client.bucket(GCS_BUCKET)
        
        # Try each possible path until we find one that exists
        for path in possible_paths:
            logger.info(f"[{request_id}] Trying GCS path: {path}")
            blob = bucket.blob(path)
            
            if blob.exists():
                logger.info(f"[{request_id}] Found file at path: {path}")
                object_path = path
                
                # Determine content type
                content_type = blob.content_type
                if not content_type:
                    # Try to determine from filename
                    if filename.lower().endswith(('.jpg', '.jpeg')):
                        content_type = "image/jpeg"
                    elif filename.lower().endswith('.png'):
                        content_type = "image/png"
                    elif filename.lower().endswith('.gif'):
                        content_type = "image/gif"
                    else:
                        # Default fallback
                        content_type = "image/jpeg"
                
                # Get file size for logging
                file_size = blob.size
                logger.info(f"[{request_id}] File size: {file_size} bytes, Content-Type: {content_type}")
                
                # Download the content
                content = blob.download_as_bytes()
                break
        
        if not content:
            # If we've tried all paths and none worked, log the error and return 404
            paths_tried = ", ".join(possible_paths)
            logger.error(f"[{request_id}] GCS file not found in any of these paths: {paths_tried}")
            raise HTTPException(status_code=404, detail="File not found in GCS bucket")
        
        # Create response with appropriate headers for caching
        response = StreamingResponse(io.BytesIO(content), media_type=content_type)
        
        # Add caching headers - cache for 1 day but revalidate
        response.headers["Cache-Control"] = "public, max-age=86400, must-revalidate"
        
        # Add ETag for cache validation (simple hash of the content)
        etag = hashlib.md5(content).hexdigest()
        response.headers["ETag"] = f'"{etag}"'
        
        # Add Last-Modified header
        # Get the blob's updated timestamp if possible, otherwise use current time
        last_modified = blob.updated
        if not last_modified:
            last_modified = datetime.datetime.now(datetime.timezone.utc)
        response.headers["Last-Modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        logger.info(f"[{request_id}] Successfully served file from GCS path: {object_path}")
        return response
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error proxying file from GCS: {str(e)}")
        # Log full traceback for critical errors
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to proxy file from GCS: {str(e)}")



# Global data structure to cache image metadata for searching
image_metadata_cache = []  # Will store dicts with folder, name, url, mimetype, etc.
last_cache_update = None
storage_client = None

# Helper function to update the image metadata cache
def update_image_metadata_cache():
    global image_metadata_cache, last_cache_update
    
    # Check if cache is already up-to-date
    current_time = datetime.datetime.now()
    if last_cache_update and (current_time - last_cache_update).total_seconds() < 60:
        return
    
    # Get the GCS bucket name from environment variable or use default
    bucket_name = os.environ.get("GCS_BUCKET", "photoportfolio-uploads")
    
    # Initialize storage client if needed
    global storage_client
    if not storage_client:
        storage_client = storage.Client()
    
    # Get all blobs in the bucket with folders/ prefix
    logger.info(f"Listing blobs from bucket: {bucket_name} with prefix 'folders/'")
    blobs = list(storage_client.list_blobs(bucket_name, prefix="folders/"))
    logger.info(f"Found {len(blobs)} blobs in the bucket")
    
    # Extract folder names and organize images by folder
    image_metadata_cache = []
    for blob in blobs:
        # Skip the folders/ prefix itself
        if blob.name == "folders/":
            continue
        
        # Extract folder name and filename from path
        path_parts = blob.name.split('/')
        if len(path_parts) > 2 and path_parts[0] == "folders":
            folder_name = path_parts[1]
            filename = path_parts[2]
            
            # Skip if this is a folder reference and not an actual file
            if not filename or filename.endswith('/'):
                continue
            
            # Create public URL for the image
            url = f"https://storage.googleapis.com/{bucket_name}/{blob.name}"
            
            # Add image metadata
            image_info = {
                "folder": folder_name,
                "name": filename,
                "url": url,
                "storage_path": blob.name,
                "size": blob.size,
                "updated": blob.updated.isoformat() if blob.updated else None
            }
            
            image_metadata_cache.append(image_info)
    
    # Update timestamp
    last_cache_update = current_time
    logger.info(f"Updated search metadata cache with {len(image_metadata_cache)} items")

@app.get("/api/proxy-image")
async def proxy_image(path: str):
    try:
        logger.info(f"Proxying image from GCS path: {path}")
        bucket_name = GCS_BUCKET
        
        # Initialize storage client if needed
        global storage_client
        if not storage_client:
            storage_client = storage.Client()
        
        # Get the blob from GCS
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(path)
        
        # Check if blob exists
        if not blob.exists():
            logger.error(f"Image not found in GCS: {path}")
            return {"error": "Image not found"}
        
        # Download the blob content
        content = blob.download_as_bytes()
        
        # Determine the content type based on file extension
        if path.lower().endswith(".png"):
            content_type = "image/png"
        elif path.lower().endswith(".gif"):
            content_type = "image/gif"
        elif path.lower().endswith(".tif") or path.lower().endswith(".tiff"):
            # TIFF files aren't natively supported by browsers, but we'll send the correct MIME type
            content_type = "image/tiff"
        elif path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
            content_type = "image/jpeg"
        else:
            # Default to JPEG for unknown extensions
            content_type = "image/jpeg"
            
        # Create a streaming response
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Cache-Control": "public, max-age=86400"
            }
        )
    except Exception as e:
        logger.error(f"Error proxying image: {str(e)}")
        return {"error": str(e)}

# Add a signed URL endpoint for compatibility with frontend - log when this is called
@app.post("/api/signed-url")
async def get_signed_url(request: Request):
    # Log the entire request for debugging
    body = await request.json()
    logger.info(f"SIGNED URL REQUEST: Received request for signed URL: {body}")
    logger.info(f"SIGNED URL REQUEST HEADERS: {dict(request.headers)}")

# Google Cloud Vision client - initialize with explicit credentials if needed
try:
    vision_client = vision.ImageAnnotatorClient()
    storage_client = storage.Client()
    logger.info("Successfully initialized Google Cloud clients")
except Exception as e:
    logger.error(f"Failed to initialize Google Cloud clients: {str(e)}")
    logger.warning("Will use fallback filename-based annotation instead of Vision API")
    vision_client = None
    storage_client = None

# Helper function to analyze image with Google Cloud Vision API
def analyze_image_with_vision(image_path: str) -> AnnotationResponse:
    """Analyze an image using Google Cloud Vision API to extract content and location information"""
    try:
        # Prepare the image
        full_path = Path(image_path).absolute()
        logger.info(f"Analyzing image with Vision API: {full_path}")
        
        with open(full_path, "rb") as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        
        # Request multiple types of annotations from the Vision API
        features = [
            vision.Feature(type_=vision.Feature.Type.LABEL_DETECTION),
            vision.Feature(type_=vision.Feature.Type.LANDMARK_DETECTION),
            vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION),
            vision.Feature(type_=vision.Feature.Type.IMAGE_PROPERTIES),
            vision.Feature(type_=vision.Feature.Type.SAFE_SEARCH_DETECTION),
        ]
        
        # Perform the API request
        response = vision_client.annotate_image({"image": image, "features": features})
        logger.info(f"Received Vision API response for {os.path.basename(image_path)}")
        
        # Extract labels for tags
        tags = [label.description.capitalize() for label in response.label_annotations[:8]]
        
        # Extract objects for better description
        objects = [obj.name.capitalize() for obj in response.localized_object_annotations[:5]]
        
        # Extract landmarks for location
        location_tag = None
        if response.landmark_annotations:
            location_tag = response.landmark_annotations[0].description
        
        # Generate a comprehensive description based on the objects and labels
        if objects:
            description = f"Image containing {', '.join(objects)}"
        elif tags:
            description = f"Image of {', '.join(tags[:3])}"
        else:
            # Fall back to filename if no objects or labels detected
            filename = os.path.basename(image_path)
            base_name, _ = os.path.splitext(filename)
            parsed_name = base_name.replace('_', ' ').replace('-', ' ')
            description = f"Image {parsed_name[:30]}"
        
        # Check if image is appropriate (safe search)
        if response.safe_search_annotation:
            adult_score = response.safe_search_annotation.adult
            violence_score = response.safe_search_annotation.violence
            racy_score = response.safe_search_annotation.racy
            
            # Log any potential content concerns
            if adult_score >= vision.SafeSearchAnnotation.Likelihood.POSSIBLE or \
               violence_score >= vision.SafeSearchAnnotation.Likelihood.POSSIBLE or \
               racy_score >= vision.SafeSearchAnnotation.Likelihood.POSSIBLE:
                logger.warning(f"Image content warning for {os.path.basename(image_path)}")
        
        # Log the results
        logger.info(f"Vision analysis for {os.path.basename(image_path)}: ")
        logger.info(f"  Description: {description}")
        logger.info(f"  Location: {location_tag}")
        logger.info(f"  Tags: {tags}")
        
        return AnnotationResponse(
            description=description,
            location_tag=location_tag,
            tags=tags
        )
    except Exception as e:
        logger.error(f"Error in Google Vision API annotation: {str(e)}")
        # Fall back to basic filename parsing if Vision API fails
        return analyze_image_with_filename(image_path)

# Fallback function that analyzes images based on filename when Vision API is unavailable
def analyze_image_with_filename(image_path: str) -> AnnotationResponse:
    """Analyze an image using filename parsing as a fallback when Vision API is unavailable"""
    try:
        # Extract filename without extension
        filename = os.path.basename(image_path)
        base_name, _ = os.path.splitext(filename)
        
        # Replace underscores and hyphens with spaces for better readability
        parsed_name = base_name.replace('_', ' ').replace('-', ' ')
        
        # Generate basic tags from the filename
        # Split the filename by spaces and use words as tags
        words = parsed_name.split()
        tags = [word.capitalize() for word in words if len(word) > 2][:5]  # Take up to 5 meaningful words
        
        # Try to extract location info if present (look for location indicators)
        location_indicators = ['at', 'in', 'near', 'from']
        location_tag = None
        
        for indicator in location_indicators:
            if indicator in words:
                idx = words.index(indicator)
                if idx < len(words) - 1:
                    # Take up to 3 words after the location indicator
                    location_words = words[idx+1:idx+4]
                    location_tag = ' '.join(word.capitalize() for word in location_words)
                    break
        
        # Generate a simple description
        if len(tags) > 0:
            description = f"Image of {' '.join(tags[:3])}"
        else:
            description = f"Image {parsed_name[:30]}"
            
        logger.info(f"Fallback annotation for {filename}: {description}, location: {location_tag}, tags: {tags}")
        
        return AnnotationResponse(
            description=description,
            location_tag=location_tag,
            tags=tags
        )
    except Exception as e:
        logger.error(f"Error in fallback image annotation: {str(e)}")
        return AnnotationResponse(description="Image", tags=["Photo"])

# Add an endpoint to annotate an image
@app.post("/api/annotate-image/")
async def annotate_image(request: AnnotateImageRequest):
    """Annotate an image using filename analysis (placeholder for Vision API)"""
    logger.info(f"Annotate image request for {request.filename} from folder {request.folder}")
    
    try:
        # Just use the filename directly for annotation - no need to check if file exists
        # This ensures we can annotate based on filenames even if the actual file is not accessible
        filename = request.filename
        
        # Debug logging
        logger.info(f"Processing annotation for filename: {filename}")
        
        # Create basic annotations from the filename
        base_name, _ = os.path.splitext(filename)
        parsed_name = base_name.replace('_', ' ').replace('-', ' ')
        
        # Extract meaningful words for tags
        words = parsed_name.split()
        meaningful_words = [word.capitalize() for word in words if len(word) > 2 and not word.isdigit()]
        tags = meaningful_words[:5]  # Take up to 5 meaningful words
        
        # Try to identify a subject
        wildlife_keywords = ['bird', 'deer', 'duck', 'owl', 'eagle', 'hawk', 'fox', 'wolf', 'bear', 'junco', 'mallard', 'doe']
        landscape_keywords = ['mountain', 'lake', 'river', 'forest', 'sunset', 'sunrise', 'beach', 'ocean', 'sky']
        
        # Identify subjects in the filename
        subjects = []
        for word in words:
            word_lower = word.lower()
            if word_lower in wildlife_keywords:
                subjects.append(word.capitalize())
            elif word_lower in landscape_keywords:
                subjects.append(word.capitalize())
        
        # Generate description
        if subjects:
            description = f"Image of {', '.join(subjects)}"
        elif len(tags) > 0:
            description = f"Image of {' '.join(tags[:3])}"
        else:
            description = f"Image {parsed_name[:30]}"
        
        # Create a location tag if possible
        location_tag = None
        if 'sunrise' in parsed_name.lower() or 'sunset' in parsed_name.lower():
            location_tag = "Nature Scene"
        
        # Create the response
        response_data = {
            "description": description,
            "location_tag": location_tag,
            "tags": tags or subjects or ["Photo", "Image"]
        }
        
        logger.info(f"Generated annotations: {response_data}")
        
        # Return the annotations
        return response_data
    except Exception as e:
        logger.error(f"Error annotating image: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error annotating image: {str(e)}"}
        )

# Add an endpoint to delete an image
@app.post("/api/delete-image/")
async def delete_image(request: DeleteImageRequest):
    """Delete an image from a folder"""
    logger.info(f"Delete image request received - Folder: {request.folder}, Filename: {request.filename}")
    
    try:
        # Handle case where filename includes folder path (folder/filename.jpg format)
        actual_folder = request.folder
        actual_filename = request.filename
        
        # If filename contains a slash, it might include the folder path already
        if '/' in request.filename:
            # Check if this is already a folder/filename format
            parts = request.filename.split('/')
            if len(parts) == 2:
                actual_folder = parts[0]
                actual_filename = parts[1]
                logger.info(f"Extracted folder '{actual_folder}' and filename '{actual_filename}' from combined path")
        
        # Special handling for paths with 'folders/' prefix
        if actual_filename.startswith('folders/'):
            parts = actual_filename.split('/', 2)  # Split only on first two slashes
            if len(parts) >= 3:
                # Format: folders/landscape/beach.jpg
                actual_folder = parts[1]
                actual_filename = parts[2]
                logger.info(f"Extracted from 'folders/' prefix: folder '{actual_folder}', filename '{actual_filename}'")
        
        logger.info(f"Processing delete request - Resolved to Folder: {actual_folder}, Filename: {actual_filename}")
        
        deletion_success = False
        deletion_message = ""
        
        # For GCS bucket deletion
        if storage_client:
            try:
                bucket = storage_client.bucket(GCS_BUCKET)
                # Try multiple possible paths formats
                possible_paths = [
                    f"folders/{actual_folder}/{actual_filename}",  # Standard GCS path
                    f"{actual_folder}/{actual_filename}",         # Direct path without folders prefix
                    f"{request.filename}",                        # Use filename as provided
                    f"folders/{request.folder}/{request.filename}",  # Original request format with folders prefix
                    f"{request.folder}/{request.filename}"           # Original request format
                ]
                
                # Add additional path variations for better matching
                if '/' in actual_filename:
                    # If filename still has path components, try them directly
                    possible_paths.append(actual_filename)
                
                # Try with URL-decoded paths as well
                from urllib.parse import unquote
                decoded_filename = unquote(actual_filename)
                if decoded_filename != actual_filename:
                    possible_paths.append(f"folders/{actual_folder}/{decoded_filename}")
                    possible_paths.append(f"{actual_folder}/{decoded_filename}")
                
                logger.info(f"Attempting to delete using these GCS paths: {possible_paths}")
                
                deleted = False
                for blob_path in possible_paths:
                    try:
                        logger.info(f"Checking blob: {blob_path}")
                        blob = bucket.blob(blob_path)
                        
                        if blob.exists():
                            blob.delete()
                            logger.info(f"Successfully deleted blob from GCS: {blob_path}")
                            deleted = True
                            deletion_success = True
                            deletion_message = f"Image {actual_filename} deleted successfully from GCS bucket"
                            
                            # Update cache to remove the deleted image
                            for folder_key in _cached_folder_contents.keys():
                                if folder_key == actual_folder or folder_key == request.folder:
                                    logger.info(f"Updating cache for folder: {folder_key}")
                                    _cached_folder_contents[folder_key] = [
                                        img for img in _cached_folder_contents[folder_key] 
                                        if img.get('name') != actual_filename and 
                                           img.get('name') != request.filename
                                    ]
                            break
                    except Exception as blob_error:
                        logger.warning(f"Error checking blob {blob_path}: {str(blob_error)}")
                
                if not deleted:
                    logger.warning(f"No matching blob found in GCS for any of the attempted paths")
            except Exception as gcs_error:
                logger.error(f"GCS deletion error: {str(gcs_error)}")
                # Fall through to local deletion if GCS fails
        
        # Local file deletion (fallback or if GCS deletion failed)
        if not deletion_success:
            # Try multiple possible paths for the file
            possible_local_paths = [
                os.path.join("uploads", "folders", actual_folder, actual_filename),
                os.path.join("uploads", actual_folder, actual_filename),
                os.path.join("uploads", request.folder, request.filename),
                os.path.join("uploads", request.filename),
                os.path.join("static", actual_folder, actual_filename),
                os.path.join("static", request.folder, request.filename),
                os.path.join("static", request.filename)
            ]
            
            # Also try with the raw filename if it contains path components
            if '/' in actual_filename:
                possible_local_paths.append(os.path.join("uploads", actual_filename))
                possible_local_paths.append(os.path.join("static", actual_filename))
            
            logger.info(f"Trying local file paths: {possible_local_paths}")
            
            for image_path in possible_local_paths:
                if os.path.exists(image_path):
                    # Remove the file
                    try:
                        os.remove(image_path)
                        logger.info(f"Deleted local file: {image_path}")
                        deletion_success = True
                        deletion_message = f"Image {actual_filename} deleted successfully from local storage"
                        break
                    except Exception as file_error:
                        logger.error(f"Error deleting local file {image_path}: {str(file_error)}")
        
        # Final response
        if deletion_success:
            # Always update the cache to ensure UI consistency
            if actual_folder in _cached_folder_contents:
                _cached_folder_contents[actual_folder] = [
                    img for img in _cached_folder_contents[actual_folder] 
                    if img.get('name') != actual_filename
                ]
            
            return {"success": True, "message": deletion_message}
        else:
            # No file was found to delete
            logger.warning("File deletion failed - no matching file found")
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"Image not found in storage (folder: {actual_folder}, filename: {actual_filename})"}
            )
    except Exception as e:
        logger.error(f"Error in delete_image endpoint: {str(e)}")
        # For debugging, include the full error details
        import traceback
        trace = traceback.format_exc()
        logger.error(f"Full traceback: {trace}")
        
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": f"Error deleting image: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error deleting image: {str(e)}"}
        )


@app.delete("/api/folder/{folder_name}")
async def delete_folder(folder_name: str):
    """Delete a folder and all its contents"""
    logger.info(f"Delete folder request received for folder: {folder_name}")
    
    try:
        deleted_count = 0
        deletion_success = False
        
        # Normalize folder name to handle potential URL encoding or path issues
        from urllib.parse import unquote
        folder_name = unquote(folder_name.strip())
        
        # For GCS bucket deletion
        if storage_client:
            try:
                logger.info(f"Attempting to delete folder from GCS bucket: {folder_name}")
                bucket = storage_client.bucket(GCS_BUCKET)
                
                # Try multiple path formats for better reliability
                prefixes_to_try = [
                    f"{folder_name}/",                 # Direct folder
                    f"folders/{folder_name}/"         # With folders/ prefix
                ]
                
                total_deleted = 0
                
                for prefix in prefixes_to_try:
                    try:
                        logger.info(f"Listing blobs with prefix: {prefix}")
                        blobs = list(bucket.list_blobs(prefix=prefix))
                        
                        if blobs:
                            logger.info(f"Found {len(blobs)} blobs with prefix '{prefix}'")
                            # Delete all blobs in the folder
                            for blob in blobs:
                                try:
                                    blob.delete()
                                    total_deleted += 1
                                    deleted_count += 1
                                    logger.info(f"Deleted blob from GCS: {blob.name}")
                                except Exception as blob_error:
                                    logger.error(f"Error deleting blob {blob.name}: {str(blob_error)}")
                            
                            deletion_success = True
                        else:
                            logger.info(f"No blobs found with prefix '{prefix}'")
                    except Exception as prefix_error:
                        logger.error(f"Error listing blobs with prefix '{prefix}': {str(prefix_error)}")
                
                # Update cache regardless of success to maintain consistency
                if folder_name in _cached_folder_contents:
                    del _cached_folder_contents[folder_name]
                    logger.info(f"Removed folder '{folder_name}' from cache")
                
                if total_deleted > 0:
                    logger.info(f"Successfully deleted {total_deleted} files from folder {folder_name} in GCS")
                    return {"success": True, "message": f"Folder {folder_name} deleted successfully with {total_deleted} files"}
                elif deletion_success:
                    logger.info(f"Folder {folder_name} was deleted but contained no files")
                    return {"success": True, "message": f"Folder {folder_name} deleted successfully (was empty)"}
                
                # If no files were deleted in GCS, try local deletion as fallback
                logger.info("No files deleted from GCS, attempting local deletion")
            except Exception as gcs_error:
                logger.error(f"GCS folder deletion error: {str(gcs_error)}")
                # Fall through to local deletion as backup
        
        # Local folder deletion (fallback)
        try:
            logger.info(f"Attempting local folder deletion for: {folder_name}")
            
            # Try multiple path formats for better reliability
            possible_folder_paths = [
                os.path.join("uploads", "folders", folder_name),
                os.path.join("uploads", folder_name),
                os.path.join("static", folder_name)
            ]
            
            local_deleted_count = 0
            for folder_path in possible_folder_paths:
                logger.info(f"Checking local folder path: {folder_path}")
                
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    for file_name in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, file_name)
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                                local_deleted_count += 1
                                deleted_count += 1
                                logger.info(f"Deleted local file: {file_path}")
                            except Exception as file_error:
                                logger.error(f"Error deleting file {file_path}: {str(file_error)}")
                    
                    # Try to remove the empty directory
                    try:
                        os.rmdir(folder_path)
                        logger.info(f"Removed empty directory: {folder_path}")
                        deletion_success = True
                    except Exception as dir_error:
                        logger.error(f"Error removing directory {folder_path}: {str(dir_error)}")
            
            # Update cache to remove the folder
            if folder_name in _cached_folder_contents:
                del _cached_folder_contents[folder_name]
                logger.info(f"Removed folder '{folder_name}' from cache")
            
            if local_deleted_count > 0 or deletion_success:
                logger.info(f"Successfully deleted {local_deleted_count} files from folder {folder_name} locally")
                return {"success": True, "message": f"Folder {folder_name} deleted successfully with {local_deleted_count} files"}
        except Exception as local_error:
            logger.error(f"Local folder deletion error: {str(local_error)}")
        
        # If we got here and no deletion was successful, return an error
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": f"Folder {folder_name} not found or could not be deleted"})
    
    except Exception as e:
        logger.error(f"Error deleting folder: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error deleting folder: {str(e)}"}
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

# Add an endpoint to reindex the Google Cloud Storage bucket
@app.get("/api/reindex-gcs")
@app.post("/api/reindex-gcs")
async def reindex_gcs(batch_size: int = 10, folder_filter: str = None, start_after: str = None):
    """Scan the GCS bucket and update the database with image metadata.
    
    This endpoint supports batching to avoid Cloud Run timeouts:
    - batch_size: Number of images to process in a single request (default: 10)
    - folder_filter: Only process a specific folder
    - start_after: Start processing after this filename (for pagination)
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Starting GCS bucket reindexing process")
    
    # Get the GCS bucket name from environment variable or use default
    bucket_name = os.environ.get("GCS_BUCKET", "photoportfolio-uploads")
    
    # Statistics for tracking the reindexing process
    stats = {
        "request_id": request_id,
        "folders_processed": 0,
        "folders_created": 0,
        "images_processed": 0,
        "images_added": 0,
        "errors": [],
        "complete": False,
        "next_batch": {}
    }
    
    try:
        # Get global storage client
        global storage_client
        
        # If storage client isn't initialized, try to initialize it now
        if not storage_client:
            logger.info(f"[{request_id}] Storage client not initialized, attempting to initialize it now")
            try:
                storage_client = storage.Client()
                logger.info(f"[{request_id}] Successfully initialized storage client")
            except Exception as init_error:
                error_msg = f"Failed to initialize storage client: {str(init_error)}"
                logger.error(f"[{request_id}] {error_msg}")
                return JSONResponse(
                    status_code=500,
                    content={"detail": error_msg}
                )
        
        # Verify client is working by testing a simple operation
        try:
            # Test if we can list buckets (just to verify credentials)
            list(storage_client.list_buckets(max_results=1))
            logger.info(f"[{request_id}] Storage client verified working")
        except Exception as verify_error:
            error_msg = f"Storage client verification failed: {str(verify_error)}"
            logger.error(f"[{request_id}] {error_msg}")
            # Try to re-initialize
            try:
                storage_client = storage.Client()
                logger.info(f"[{request_id}] Re-initialized storage client after verification failure")
            except Exception as reinit_error:
                error_msg = f"Failed to re-initialize storage client: {str(reinit_error)}"
                logger.error(f"[{request_id}] {error_msg}")
                return JSONResponse(
                    status_code=500,
                    content={"detail": error_msg}
                )
            
        logger.info(f"[{request_id}] Accessing bucket: {bucket_name}")
        bucket = storage_client.bucket(bucket_name)
        
        # Check if bucket exists
        if not bucket.exists():
            error_msg = f"Bucket {bucket_name} does not exist"
            logger.error(f"[{request_id}] {error_msg}")
            return JSONResponse(
                status_code=404,
                content={"detail": error_msg}
            )
        
        # Get folder names to process
        folder_names = []
        
        if folder_filter:
            # Process only the specified folder
            folder_names = [folder_filter]
            logger.info(f"[{request_id}] Processing only folder: {folder_filter}")
        else:
            # Get all blobs in the bucket with folders/ prefix
            logger.info(f"[{request_id}] Listing all folders in bucket")
            blobs = storage_client.list_blobs(bucket_name, prefix="folders/")
            
            # Extract folder names
            folder_set = set()
            for blob in blobs:
                # Skip the folders/ prefix itself
                if blob.name == "folders/":
                    continue
                    
                # Extract folder name from path
                path_parts = blob.name.split('/')
                if len(path_parts) > 1 and path_parts[0] == "folders":
                    folder_set.add(path_parts[1])
            
            folder_names = sorted(folder_set)
            logger.info(f"[{request_id}] Found {len(folder_names)} folders in bucket")
        
        # Create folder directories locally if they don't exist
        uploads_dir = Path("uploads")
        if not uploads_dir.exists():
            uploads_dir.mkdir(parents=True)
        
        # Keep track of remaining items to process
        images_processed_in_batch = 0
        next_folder_index = 0
        next_start_after = None
        continue_from_folder = None
        has_more = False
        
        # Handle start_after for pagination
        if start_after and len(folder_names) > 0:
            parts = start_after.split('/')
            if len(parts) == 2:
                continue_from_folder = parts[0]
                next_start_after = parts[1]
                try:
                    next_folder_index = folder_names.index(continue_from_folder)
                except ValueError:
                    # Folder not found, start from beginning
                    next_folder_index = 0
                    next_start_after = None
        
        # Process folders batch by batch
        while next_folder_index < len(folder_names) and images_processed_in_batch < batch_size:
            folder_name = folder_names[next_folder_index]
            folder_path = uploads_dir / folder_name
            
            if not folder_path.exists():
                folder_path.mkdir(parents=True)
                stats["folders_created"] += 1
            
            logger.info(f"[{request_id}] Processing folder: {folder_name}")
            stats["folders_processed"] += 1
            
            # Get all blobs in this folder
            folder_prefix = f"folders/{folder_name}/"
            
            # If continuing from a previous batch within this folder
            if folder_name == continue_from_folder and next_start_after:
                logger.info(f"[{request_id}] Continuing from file: {next_start_after} in folder: {folder_name}")
            
            folder_blobs = list(storage_client.list_blobs(bucket_name, prefix=folder_prefix))
            folder_blobs.sort(key=lambda b: b.name)
            
            # Skip files until we reach the start_after point
            file_index = 0
            if folder_name == continue_from_folder and next_start_after:
                for i, blob in enumerate(folder_blobs):
                    filename = blob.name.split('/')[-1]
                    if filename == next_start_after:
                        file_index = i + 1  # Start with the next file
                        break
            
            # Process files in this folder up to the batch limit
            while file_index < len(folder_blobs) and images_processed_in_batch < batch_size:
                blob = folder_blobs[file_index]
                
                # Skip if this is the folder itself or not a file
                if blob.name == folder_prefix or blob.name.endswith('/'):
                    file_index += 1
                    continue
                
                try:
                    # Extract filename
                    filename = blob.name.split('/')[-1]
                    logger.info(f"[{request_id}] Processing image: {filename}")
                    
                    # Generate public URL
                    url = f"https://storage.googleapis.com/{bucket_name}/{blob.name}"
                    
                    # Get local file path
                    local_path = folder_path / filename
                    
                    # Download the image if it doesn't exist locally
                    if not local_path.exists():
                        blob.download_to_filename(str(local_path))
                        logger.info(f"[{request_id}] Downloaded {filename} to {folder_name}/{filename}")
                    
                    # Tag image with CLIP
                    candidate_tags = [
                        "Florence", "Landscape", "Wildlife", "Nature", "Photography",
                        "City", "Portrait", "Architecture", "Travel", "People",
                        "Animals", "Mountains", "River", "Sunset", "Forest",
                        "Desert", "Beach", "Night", "Street", "Art"
                    ]
                    try:
                        top_tags = tag_image_with_clip(str(local_path), candidate_tags, top_k=5)
                        tag_strings = [tag for tag, prob in top_tags]
                        logger.info(f"[{request_id}] CLIP tags for {filename}: {tag_strings}")
                    except Exception as tag_error:
                        tag_strings = []
                        logger.error(f"[{request_id}] CLIP tagging failed for {filename}: {tag_error}")

                    # Add metadata to the database (if we had one)
                    # In a real app, we would store this information in a database, including tags
                    # For now, we'll just count it as processed and log tags
                    stats["images_processed"] += 1
                    stats["images_added"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing image {blob.name}: {str(e)}"
                    logger.error(f"[{request_id}] {error_msg}")
                    logger.error(f"[{request_id}] {traceback.format_exc()}")
                    stats["errors"].append(error_msg)
                
                file_index += 1
                images_processed_in_batch += 1
                next_start_after = filename
            
            # Check if we've processed all files in this folder
            if file_index < len(folder_blobs):
                # We haven't finished this folder yet
                has_more = True
                break
            else:
                # We've finished this folder, move to the next one
                next_folder_index += 1
                next_start_after = None
                continue_from_folder = None
        
        # Check if there are more batches to process
        if next_folder_index < len(folder_names):
            has_more = True
            # Save state for next batch
            next_folder = folder_names[next_folder_index]
            stats["next_batch"] = {
                "folder_filter": folder_filter,
                "start_after": f"{next_folder}/{next_start_after}" if next_start_after else next_folder
            }
            stats["complete"] = False
        else:
            stats["complete"] = True
        
        # Return success response
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "GCS bucket reindexing batch completed" if has_more else "GCS bucket reindexing completed",
                "stats": stats,
                "has_more": has_more
            }
        )
        
    except Exception as e:
        error_msg = f"Error reindexing GCS bucket: {str(e)}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": error_msg
            }
        )

# Add a debug endpoint to check file paths
@app.get("/api/debug/check-files/{folder}/{filename}")
async def check_file_path(folder: str, filename: str):
    """Debug endpoint to check if files exist in the uploads and static directories"""
    # Check uploads directory
    uploads_path = f"uploads/{folder}/{filename}"
    uploads_exists = os.path.exists(uploads_path)
    
    # Check static directory
    static_path = f"static/{folder}/{filename}"
    static_exists = os.path.exists(static_path)
    
    # List all files in the folder for debugging
    folder_files_uploads = []
    uploads_folder_path = f"uploads/{folder}"
    if os.path.exists(uploads_folder_path):
        folder_files_uploads = os.listdir(uploads_folder_path)
    
    folder_files_static = []
    static_folder_path = f"static/{folder}"
    if os.path.exists(static_folder_path):
        folder_files_static = os.listdir(static_folder_path)
    
    return {
        "uploads_path": uploads_path,
        "uploads_exists": uploads_exists,
        "static_path": static_path,
        "static_exists": static_exists,
        "folder_files_uploads": folder_files_uploads,
        "folder_files_static": folder_files_static
    }

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

# API endpoint for semantic search
@app.get("/api/photos/semantic-search/")
async def semantic_search_photos(q: str = Query(None)):
    """Search photos by semantic query"""
    if not q or q.strip() == "":
        raise HTTPException(status_code=400, detail="Missing query parameter")
    
    query = q.strip().lower()
    logger.info(f"SEARCH API: Received query: '{query}'")
    
    # Update the metadata cache to ensure it's fresh
    update_image_metadata_cache()
    
    # If no items in cache, return empty results
    if not image_metadata_cache:
        logger.warning("SEARCH API: No items in metadata cache")
        return []
    
    results = []
    
    # Use semantic search if available
    if has_semantic_search and _semantic_model:
        try:
            # Prepare texts for embedding
            photo_texts = [f"{item['name']} {item['folder']} {' '.join(item.get('tags', []))} {item.get('location', '')}" 
                          for item in image_metadata_cache]
            
            # Get embeddings
            photo_embeddings = _semantic_model.encode(photo_texts)
            query_embedding = _semantic_model.encode([query])[0]
            
            # Compute cosine similarity
            similarities = np.dot(photo_embeddings, query_embedding) / (
                np.linalg.norm(photo_embeddings, axis=1) * np.linalg.norm(query_embedding) + 1e-8
            )
            
            # Get top matches
            matches = sorted(enumerate(similarities), key=lambda x: x[1], reverse=True)
            
            # Take top 20 matches with score > 0.2
            for idx, score in matches:
                if score > 0.2 and len(results) < 20:
                    result = dict(image_metadata_cache[idx])
                    result['score'] = float(score)
                    results.append(result)
                    
            logger.info(f"SEARCH API: Found {len(results)} semantic matches for '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"SEARCH API: Semantic search error: {str(e)}")
            # Fall back to basic search on error
    
    # Basic text matching as fallback
    logger.info("SEARCH API: Using basic text matching")
    query_terms = query.lower().split()
    
    for item in image_metadata_cache:
        # Create searchable text from metadata
        item_text = f"{item['name'].lower()} {item['folder'].lower()} {' '.join(item.get('tags', [])).lower()} {str(item.get('location', '')).lower()}"
        
        # Count matching terms
        matches = sum(term in item_text for term in query_terms)
        
        # Add to results if at least one term matches
        if matches > 0:
            score = matches / len(query_terms)  # Simple relevance score
            result = dict(item)
            result['score'] = float(score)
            results.append(result)
    
    # Sort by score descending
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # Limit to top 20
    results = results[:20]
    
    logger.info(f"SEARCH API: Found {len(results)} basic matches for '{query}'")
    return results

if __name__ == "__main__":
    try:
        # Log environment variables for debugging
        logger.info(f"Environment variables: GCS_BUCKET={os.environ.get('GCS_BUCKET')}, SERVICE_URL={os.environ.get('SERVICE_URL')}, FALLBACK_URL={os.environ.get('FALLBACK_URL')}")
        
        # Log the global variables
        logger.info(f"Global variables: GCS_BUCKET={GCS_BUCKET}, storage_client={storage_client is not None}")
        
        # Get port from environment variable for Cloud Run compatibility
        port = int(os.environ.get("PORT", 8080))
        logger.info(f"Starting server on port {port} with host 0.0.0.0")
        
        # Initialize Cloud Storage client if needed
        if storage_client is None:
            logger.info("Initializing Cloud Storage client")
            try:
                from google.cloud import storage
                storage_client = storage.Client()
                logger.info("Successfully initialized Cloud Storage client")
            except Exception as e:
                logger.error(f"Failed to initialize Cloud Storage client: {str(e)}")
        
        # Start the server without using argparse for simplicity
        import uvicorn
        uvicorn.run("simplified_app:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"Fatal error during startup: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
