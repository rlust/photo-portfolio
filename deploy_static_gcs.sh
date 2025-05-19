#!/bin/bash
# Automated deployment script for PhotoPortfolio static frontend to Google Cloud Storage
# Usage: ./deploy_static_gcs.sh <BUCKET_SUFFIX>

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <BUCKET_SUFFIX>"
  exit 1
fi

PROJECT_ID="photo-portfolio"
BUCKET_NAME="photo-portfolio-$1"
BUILD_DIR="build" # Change to 'dist' if that's your build output

# Authenticate and set project
gcloud auth login
gcloud config set project $PROJECT_ID

# Build static site (uncomment if you want to build as part of the script)
# npm run build || yarn build

# Create GCS bucket
gsutil mb -p $PROJECT_ID gs://$BUCKET_NAME || echo "Bucket may already exist. Skipping creation."

# Enable website configuration
gsutil web set -m index.html -e 404.html gs://$BUCKET_NAME

# Upload static files
gsutil rsync -R $BUILD_DIR gs://$BUCKET_NAME

# Make the site public
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME

# Output site URL
echo "\nDeployment complete! Your site is available at:"
echo "http://storage.googleapis.com/$BUCKET_NAME/index.html"
