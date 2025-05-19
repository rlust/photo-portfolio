#!/bin/bash
set -e

# Set variables
PROJECT_ID="photo-portfolio-459415"
SERVICE_NAME="photo-portfolio-production"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Authenticate with gcloud
echo "Authenticating with gcloud..."
gcloud auth configure-docker --quiet

# Build and push Docker image
echo "Building Docker image..."

# Create a temporary directory for the build context
TEMP_DIR=$(mktemp -d)

# Copy necessary files to the temp directory
cp -r backend/* "${TEMP_DIR}"/

# Navigate to the temp directory
cd "${TEMP_DIR}"

# Build the Docker image
docker build -t ${IMAGE_NAME}:latest .

# Clean up the temp directory
cd - > /dev/null
rm -rf "${TEMP_DIR}"

echo "Pushing Docker image to Container Registry..."
docker push ${IMAGE_NAME}:latest

echo "Deployment completed successfully!"
echo "Service URL: https://${SERVICE_NAME}-${PROJECT_ID}.${REGION}.run.app"
