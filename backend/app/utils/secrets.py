"""
Utility module for accessing secrets from Google Cloud Secret Manager.
"""
import os
import json
from typing import Optional, Dict, Any
from google.cloud import secretmanager

# Initialize the Secret Manager client
client = secretmanager.SecretManagerServiceClient()

def get_secret(secret_id: str, version_id: str = "latest") -> str:
    """
    Get a secret from Google Cloud Secret Manager.

    Args:
        secret_id: The ID of the secret to access
        version_id: Version of the secret (defaults to 'latest')

    Returns:
        The secret payload as a string
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
    
    # Build the resource name of the secret version
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    
    try:
        # Access the secret version
        response = client.access_secret_version(request={"name": name})
        # Return the decoded payload
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        raise Exception(f"Failed to access secret {secret_id}: {str(e)}")

def get_secret_json(secret_id: str, version_id: str = "latest") -> Dict[str, Any]:
    """
    Get a JSON secret from Google Cloud Secret Manager and parse it as a dictionary.

    Args:
        secret_id: The ID of the secret to access
        version_id: Version of the secret (defaults to 'latest')

    Returns:
        The parsed JSON secret as a dictionary
    """
    secret_value = get_secret(secret_id, version_id)
    try:
        return json.loads(secret_value)
    except json.JSONDecodeError as e:
        raise ValueError(f"Secret {secret_id} is not valid JSON: {str(e)}")

def get_database_credentials() -> Dict[str, str]:
    """
    Get database credentials from Secret Manager.
    
    Returns:
        Dictionary containing database connection parameters
    """
    try:
        # Try to get all database credentials from a single secret
        return get_secret_json("database-credentials")
    except Exception as e:
        # Fall back to individual secrets if the combined secret doesn't exist
        print(f"Warning: Could not get database credentials from secret: {str(e)}")
        return {
            "DB_USER": os.getenv("DB_USER", ""),
            "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
            "DB_HOST": os.getenv("DB_HOST", ""),
            "DB_PORT": os.getenv("DB_PORT", "5432"),
            "DB_NAME": os.getenv("DB_NAME", ""),
        }
