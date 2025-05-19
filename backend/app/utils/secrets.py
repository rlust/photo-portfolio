"""
Utility module for accessing secrets from Google Cloud Secret Manager or environment variables.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Lazy initialization for Secret Manager client
_secret_client = None

def _get_secret_client():
    """Lazy initializer for Secret Manager client"""
    global _secret_client
    if _secret_client is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            try:
                from google.cloud import secretmanager
                _secret_client = secretmanager.SecretManagerServiceClient()
                logger.info("Initialized Google Cloud Secret Manager client")
            except (ImportError, Exception) as e:
                logger.warning(f"Failed to initialize Secret Manager client: {e}. Using environment variables.")
        else:
            logger.info("Not running in Google Cloud. Using environment variables for configuration.")
    return _secret_client

def get_secret(secret_id: str, version_id: str = "latest") -> str:
    """
    Get a secret from Google Cloud Secret Manager or environment variables.

    Args:
        secret_id: The ID of the secret to access (also used as environment variable name)
        version_id: Version of the secret (unused when using environment variables)

    Returns:
        The secret payload as a string
    """
    # First try to get from environment variables
    secret_value = os.getenv(secret_id)
    if secret_value is not None:
        logger.debug(f"Found secret {secret_id} in environment variables")
        return secret_value
    
    # If not in environment variables and we have a Secret Manager client, try that
    client = _get_secret_client()
    if client is not None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT environment variable not set, falling back to environment variables")
            return secret_value or ""
        
        # Build the resource name of the secret version
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        
        try:
            # Access the secret version
            response = client.access_secret_version(request={"name": name})
            
            # Parse the payload and decode it as UTF-8
            payload = response.payload.data.decode("UTF-8")
            logger.debug(f"Retrieved secret {secret_id} from Secret Manager")
            return payload
        except Exception as e:
            logger.warning(f"Error retrieving secret {secret_id} from Secret Manager: {e}")
            return secret_value or ""  # Return environment variable (which may be None) as fallback
    
    # If we get here, we couldn't find the secret
    logger.warning(f"Secret {secret_id} not found in environment variables and Secret Manager is not available")
    return ""  # Return empty string instead of raising an exception

def get_secret_json(secret_id: str, version_id: str = "latest") -> Dict[str, Any]:
    """
    Get a JSON secret from Google Cloud Secret Manager and parse it as a dictionary.

    Args:
        secret_id: The ID of the secret to access
        version_id: Version of the secret (defaults to 'latest')

    Returns:
        The parsed JSON secret as a dictionary or empty dict if not found/invalid
    """
    secret_value = get_secret(secret_id, version_id)
    if not secret_value:
        logger.warning(f"No value found for secret {secret_id}, returning empty dict")
        return {}
    
    try:
        return json.loads(secret_value)
    except json.JSONDecodeError as e:
        logger.warning(f"Secret {secret_id} is not valid JSON: {str(e)}, returning empty dict")
        return {}

def get_database_credentials() -> Dict[str, str]:
    """
    Get database credentials from environment variables.
    
    Returns:
        Dictionary containing database connection parameters
    """
    logger.info("Getting database credentials from environment variables")
    return {
        "DB_USER": os.getenv("DB_USER", ""),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": os.getenv("DB_PORT", "5432"),
        "DB_NAME": os.getenv("DB_NAME", "")
    }
