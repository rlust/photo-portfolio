"""
Google Cloud Storage utilities for the Photo Portfolio application.
"""

import os
import logging
from typing import Optional, BinaryIO, Tuple
from google.cloud import storage
from google.oauth2 import service_account
from ..config import settings

# Configure logging
logger = logging.getLogger(__name__)

class GCSClient:
    """A client for interacting with Google Cloud Storage."""
    
    def __init__(self, bucket_name: Optional[str] = None):
        """Initialize the GCS client.
        
        Args:
            bucket_name: The name of the GCS bucket to use. If not provided,
                the bucket name from settings will be used.
        """
        self.bucket_name = bucket_name or settings.GCS_BUCKET
        if not self.bucket_name:
            raise ValueError("GCS bucket name must be provided or set in settings")
        
        # Initialize the GCS client
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            # Use the service account key file if specified
            self.client = storage.Client.from_service_account_json(
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
        else:
            # Use application default credentials
            self.client = storage.Client()
        
        # Get the bucket
        self.bucket = self.client.bucket(self.bucket_name)
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        destination_blob_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """Upload a file to the GCS bucket.
        
        Args:
            file_obj: A file-like object to upload.
            destination_blob_name: The name to give the blob in GCS.
            content_type: The content type of the file (e.g., 'image/jpeg').
            metadata: Optional metadata to attach to the blob.
            
        Returns:
            str: The public URL of the uploaded file.
        """
        try:
            blob = self.bucket.blob(destination_blob_name)
            
            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            
            # Set metadata if provided
            if metadata:
                blob.metadata = metadata
            
            # Upload the file
            blob.upload_from_file(file_obj, rewind=True)
            
            # Make the blob publicly accessible
            blob.make_public()
            
            logger.info(f"File {destination_blob_name} uploaded to {self.bucket_name}.")
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Error uploading file to GCS: {e}")
            raise
    
    def delete_file(self, blob_name: str) -> bool:
        """Delete a file from the GCS bucket.
        
        Args:
            blob_name: The name of the blob to delete.
            
        Returns:
            bool: True if the file was deleted, False otherwise.
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"File {blob_name} deleted from {self.bucket_name}.")
            return True
        except Exception as e:
            logger.error(f"Error deleting file from GCS: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> list:
        """List all files in the GCS bucket with the given prefix.
        
        Args:
            prefix: Optional prefix to filter files.
            
        Returns:
            list: A list of blob names.
        """
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing files in GCS: {e}")
            return []

# Create a singleton instance of the GCS client
try:
    gcs_client = GCSClient()
except Exception as e:
    logger.warning(f"Failed to initialize GCS client: {e}")
    gcs_client = None
