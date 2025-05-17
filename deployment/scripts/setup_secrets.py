#!/usr/bin/env python3
"""
Script to set up secrets in Google Cloud Secret Manager.

This script creates or updates the following secrets:
- database-credentials: JSON containing all database connection parameters
- app-secret-key: Application secret key for sessions and tokens
"""
import os
import json
import argparse
from google.cloud import secretmanager
from google.api_core.exceptions import AlreadyExists, NotFound

def create_secret(project_id: str, secret_id: str) -> str:
    """
    Create a new secret in Secret Manager if it doesn't exist.
    
    Args:
        project_id: Google Cloud project ID
        secret_id: ID of the secret to create
        
    Returns:
        The full resource name of the secret
    """
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project_id}"
    
    # Build the resource name of the secret
    secret_name = f"{parent}/secrets/{secret_id}"
    
    try:
        # Try to access the secret to check if it exists
        client.get_secret(request={"name": secret_name})
        print(f"Secret {secret_id} already exists, it will be updated")
        return secret_name
    except NotFound:
        # Secret doesn't exist, create it
        print(f"Creating secret: {secret_id}")
        
        # Create the secret
        secret = {
            "replication": {
                "automatic": {}
            }
        }
        
        response = client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": secret,
            }
        )
        
        print(f"Created secret: {response.name}")
        return response.name

def add_secret_version(project_id: str, secret_id: str, payload: str) -> None:
    """
    Add a new version to an existing secret.
    
    Args:
        project_id: Google Cloud project ID
        secret_id: ID of the secret
        payload: The secret payload as a string
    """
    client = secretmanager.SecretManagerServiceClient()
    
    # Build the resource name of the secret
    parent = f"projects/{project_id}/secrets/{secret_id}"
    
    # Add the secret version
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {
                "data": payload.encode("UTF-8"),
            },
        }
    )
    
    print(f"Added secret version: {response.name}")

def setup_database_credentials(project_id: str) -> None:
    """
    Set up the database credentials in Secret Manager.
    
    Args:
        project_id: Google Cloud project ID
    """
    print("\n=== Setting up database credentials ===")
    
    # Get database credentials from environment or prompt
    db_config = {
        "DB_USER": os.getenv("DB_USER") or input("Enter database username: ").strip(),
        "DB_PASSWORD": os.getenv("DB_PASSWORD") or input("Enter database password: ").strip(),
        "DB_HOST": os.getenv("DB_HOST") or input("Enter database host [localhost]: ").strip() or "localhost",
        "DB_PORT": os.getenv("DB_PORT") or input("Enter database port [5432]: ").strip() or "5432",
        "DB_NAME": os.getenv("DB_NAME") or input("Enter database name [photo_portfolio]: ").strip() or "photo_portfolio",
    }
    
    # Create or update the secret
    secret_id = "database-credentials"
    create_secret(project_id, secret_id)
    add_secret_version(project_id, secret_id, json.dumps(db_config, indent=2))
    
    print("Database credentials have been stored in Secret Manager")

def setup_app_secret_key(project_id: str) -> None:
    """
    Set up the application secret key in Secret Manager.
    
    Args:
        project_id: Google Cloud project ID
    """
    print("\n=== Setting up application secret key ===")
    
    import secrets
    
    # Generate a secure random secret key
    secret_key = secrets.token_urlsafe(64)
    
    # Create or update the secret
    secret_id = "app-secret-key"
    create_secret(project_id, secret_id)
    add_secret_version(project_id, secret_id, secret_key)
    
    print("Application secret key has been stored in Secret Manager")

def main():
    parser = argparse.ArgumentParser(description="Set up secrets in Google Cloud Secret Manager")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    args = parser.parse_args()
    
    # Set up database credentials
    setup_database_credentials(args.project_id)
    
    # Set up application secret key
    setup_app_secret_key(args.project_id)
    
    print("\n=== Secret setup complete ===")
    print("\nNext steps:")
    print("1. Grant the Cloud Run service account access to these secrets:")
    print(f"   - projects/{args.project_id}/secrets/database-credentials")
    print(f"   - projects/{args.project_id}/secrets/app-secret-key")
    print("2. Update your Cloud Run service to use these secrets as environment variables")
    print("3. Set the USE_SECRET_MANAGER environment variable to 'true'")

if __name__ == "__main__":
    main()
