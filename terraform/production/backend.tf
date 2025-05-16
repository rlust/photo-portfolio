terraform {
  backend "gcs" {
    # These values will be provided during initialization
    # Example: terraform init \
    #   -backend-config="bucket=my-terraform-state-bucket" \
    #   -backend-config="prefix=production/photo-portfolio" \
    #   -backend-config="credentials=path/to/credentials.json"
    
    # Enable state locking
    lock = true
    
    # Enable encryption
    encryption_key = null  # Use Google-managed encryption key
  }
}

# This file defines the backend configuration for storing Terraform state in Google Cloud Storage.
# The actual values should be provided during initialization using the -backend-config flag.
#
# Required backend configuration variables:
# - bucket: The name of the GCS bucket to store the state file
# - prefix: The path prefix for the state file (e.g., "production/photo-portfolio")
# - credentials: (Optional) Path to the service account key file if not using application default credentials
