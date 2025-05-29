"""
Google Cloud Storage utility module with local fallback.
"""

import os
import json
import logging
import datetime
from typing import Optional, BinaryIO, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Google Cloud libraries
try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound
    from google.auth.exceptions import DefaultCredentialsError
    GCS_AVAILABLE = True
except ImportError:
    logger.warning("Google Cloud Storage libraries not available")
    GCS_AVAILABLE = False

class GCSClient:
    """
    A client for interacting with Google Cloud Storage with local fallback.
    """
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize the GCS client with the specified bucket name.
        
        Args:
            bucket_name: Name of the GCS bucket to use
        """
        self._initialized = False
        self._bucket = None
        self._client = None
        
        # Get bucket name from environment if not provided
        self.bucket_name = bucket_name or os.environ.get("GCS_BUCKET", "photoportfolio-uploads")
        
        # Try to initialize the GCS client
        if GCS_AVAILABLE:
            try:
                # Check if running in Google Cloud environment
                project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", None)
                
                if project_id:
                    # When running in Cloud Run, use default credentials
                    logger.info(f"Running in Google Cloud environment with project ID: {project_id}")
                    self._client = storage.Client(project=project_id)
                else:
                    # When running locally, try to use default credentials or ADC
                    try:
                        self._client = storage.Client()
                        logger.info("Using local default credentials for GCS")
                    except Exception as cred_error:
                        logger.warning(f"Failed to authenticate with default credentials: {str(cred_error)}")
                        # Try explicit credentials as a last resort
                        try:
                            from google.oauth2 import service_account
                            credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                            if credentials_path and os.path.exists(credentials_path):
                                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                                self._client = storage.Client(credentials=credentials, project=project_id)
                                logger.info("Using explicit service account credentials for GCS")
                            else:
                                raise ValueError("No valid credentials found")
                        except Exception as explicit_error:
                            logger.error(f"Failed to authenticate with explicit credentials: {str(explicit_error)}")
                            raise
                
                # Get bucket reference
                self._bucket = self._client.bucket(self.bucket_name)
                
                # Check if bucket exists, create it if it doesn't
                if not self._bucket.exists():
                    logger.info(f"Bucket {self.bucket_name} does not exist, creating it")
                    self._bucket = self._client.create_bucket(self.bucket_name)
                
                self._initialized = True
                logger.info(f"GCS client initialized for bucket: {self.bucket_name}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize GCS client: {str(e)}")
                logger.info("Will use local storage as fallback")
        else:
            logger.warning("GCS support not available, using local storage")
            
        # Create local static directory for fallback
        os.makedirs("static", exist_ok=True)
        
    @property
    def is_initialized(self) -> bool:
        """Check if the GCS client is properly initialized."""
        return self._initialized
        
    @property
    def bucket(self):
        """Get the current GCS bucket."""
        if not self._initialized:
            raise ValueError("GCS client not initialized")
        return self._bucket
    
    def upload_file(
        self, file_obj: BinaryIO, destination_blob_name: str, 
        content_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload a file to Google Cloud Storage with local fallback.
        
        Args:
            file_obj: A file-like object to upload
            destination_blob_name: The name to give the blob in GCS
            content_type: The content type of the file
            metadata: Optional metadata to attach to the blob
            
        Returns:
            The URL of the uploaded file (GCS URL or local URL as fallback)
        """
        try:
            # Parse folder and filename from the destination path
            parts = destination_blob_name.split('/')
            if len(parts) > 1:
                folder = parts[0]
                filename = parts[-1]
            else:
                folder = 'default'
                filename = destination_blob_name
            
            # Log original input for debugging
            logger.info(f"Original upload request: folder={folder}, filename={filename}")
                
            # Improved filename sanitization for GCS compatibility
            import re
            import uuid
            import hashlib
            import base64
            from urllib.parse import quote
            
            # Keep the original values for metadata
            original_folder = folder
            original_filename = filename
            
            # Generate completely safe folder and filenames that will never cause GCS issues
            
            # 1. Create a hash-based unique identifier to avoid any character issues
            # Use a combination of the original filename and a timestamp for uniqueness
            timestamp = str(int(time.time()))
            unique_hash = hashlib.md5(f"{filename}{timestamp}".encode()).hexdigest()[:10]
            
            # 2. Extract the extension (preserve case but ensure it's clean)
            name_parts = os.path.splitext(filename)
            extension = name_parts[1].lower() if len(name_parts) > 1 and name_parts[1] else '.jpg'
            
            # 3. Create a completely safe filename format: photo_[hash]_[timestamp][ext]
            safe_folder = re.sub(r'[^a-zA-Z0-9]', '_', folder).strip('_')
            if not safe_folder:
                safe_folder = 'photos'
                
            # 4. Make sure the safe filename has no problematic characters at all
            safe_filename = f"photo_{unique_hash}_{timestamp}{extension}"
            
            # Log the sanitized values for debugging
            logger.info(f"Sanitized for GCS: folder={safe_folder}, filename={safe_filename}")
        
            # Create a safe path for storage but keep all original values in metadata
            safe_destination = f"{safe_folder}/{safe_filename}"
            
            # Add comprehensive metadata for reference and debugging
            if metadata is None:
                metadata = {}
                
            # Store all original values in metadata
            metadata['original_path'] = destination_blob_name
            metadata['original_folder'] = original_folder
            metadata['original_filename'] = original_filename
            metadata['safe_folder'] = safe_folder
            metadata['safe_filename'] = safe_filename
            metadata['sanitization_timestamp'] = timestamp
            
            # Log the final destination path
            logger.info(f"Final GCS destination: {safe_destination}")
        except Exception as e:
            logger.error(f"Error during filename sanitization: {str(e)}")
            # If anything fails during sanitization, use a completely safe fallback approach
            timestamp = str(int(time.time()))
            random_id = str(uuid.uuid4())[:8]
            safe_folder = "photos"
            safe_filename = f"backup_{timestamp}_{random_id}.jpg"
            safe_destination = f"{safe_folder}/{safe_filename}"
            
            if metadata is None:
                metadata = {}
            metadata['original_path'] = destination_blob_name
            metadata['error_during_sanitization'] = str(e)
            
            logger.warning(f"Using fallback safe path: {safe_destination}")
        
        # Check if GCS is available and initialized
        if not self._initialized:
            logger.warning("GCS client not initialized, using local storage fallback")
            return self._save_to_local_storage(file_obj, safe_folder, safe_filename, metadata)
        
        # Try uploading to GCS with improved error handling
        try:
            # Reset file cursor to beginning to ensure complete file is uploaded
            file_obj.seek(0)
            
            # Use the sanitized path for GCS operations
            blob = self._bucket.blob(safe_destination)
            
            # Set content type if provided, or guess from filename
            if content_type:
                blob.content_type = content_type
            else:
                import mimetypes
                guessed_type = mimetypes.guess_type(filename)[0]
                if guessed_type:
                    blob.content_type = guessed_type
                    logger.info(f"Guessed content type: {guessed_type}")
                else:
                    blob.content_type = 'image/jpeg'  # Default for photos
            
            # Set metadata with size limitations (GCS metadata has size limits)
            if metadata:
                # Ensure metadata values are strings and truncate if too long
                sanitized_metadata = {}
                for key, value in metadata.items():
                    # Convert to string and limit size to avoid metadata limits
                    str_value = str(value)
                    if len(str_value) > 1024:  # GCS metadata value size limit
                        str_value = str_value[:1021] + '...'
                    sanitized_metadata[key] = str_value
                blob.metadata = sanitized_metadata
            
            # Upload the file with retry mechanism
            max_retries = 3
            retry_count = 0
            upload_success = False
            
            while retry_count < max_retries and not upload_success:
                try:
                    # Attempt upload with appropriate content type
                    if blob.content_type:
                        blob.upload_from_file(file_obj, content_type=blob.content_type)
                    else:
                        blob.upload_from_file(file_obj)
                    upload_success = True
                except Exception as upload_error:
                    retry_count += 1
                    logger.warning(f"Upload attempt {retry_count} failed: {str(upload_error)}")
                    if retry_count >= max_retries:
                        raise  # Re-raise the last exception if all retries failed
                    time.sleep(1)  # Brief pause before retry
                    file_obj.seek(0)  # Reset file pointer for next attempt
            
            # Make the blob publicly accessible
            blob.make_public()
            logger.info(f"Successfully uploaded {destination_blob_name} to GCS as {safe_destination}")
            
            # Return the public URL
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Error uploading file to GCS: {str(e)}")
            logger.info("Falling back to local storage")
            return self._save_to_local_storage(file_obj, safe_folder, safe_filename, metadata)
    
    def _save_to_local_storage(self, file_obj: BinaryIO, folder: str, filename: str, 
                               metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Save a file to local storage as a fallback when GCS is unavailable.
        
        Args:
            file_obj: A file-like object to save
            folder: The folder name
            filename: The filename
            metadata: Optional metadata to store alongside the file
            
        Returns:
            The local URL path to the saved file
        """
        # Create local static folder
        static_folder = os.path.join("static", folder)
        os.makedirs(static_folder, exist_ok=True)
        local_path = os.path.join(static_folder, filename)
        
        # Save the file locally
        try:
            file_obj.seek(0)  # Reset file pointer to beginning
        except Exception:
            # Some file objects might not be seekable
            pass
            
        with open(local_path, 'wb') as f:
            f.write(file_obj.read())
        
        # Save metadata to a companion file if provided
        if metadata:
            meta_path = f"{local_path}.meta.json"
            with open(meta_path, 'w') as f:
                json.dump({
                    **metadata,
                    "stored_locally": True,
                    "storage_time": datetime.datetime.now().isoformat()
                }, f, indent=2)
        
        logger.info(f"Successfully saved file to local storage: {local_path}")
        # Return a local URL path that includes 'local:' prefix to indicate local storage
        return f"local:/static/{folder}/{filename}"
