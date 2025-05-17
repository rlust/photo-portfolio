#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="photo-portfolio-backend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
DB_INSTANCE=""
DB_REGION="us-central1"

# Function to display help
show_help() {
    echo -e "${YELLOW}Deploy Photo Portfolio Backend to Google Cloud Run${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --project-id PROJECT_ID       Google Cloud project ID (required)"
    echo "  -r, --region REGION             Google Cloud region (default: us-central1)"
    echo "  -s, --service-name NAME         Service name (default: photo-portfolio-backend)"
    echo "  -i, --db-instance INSTANCE      Cloud SQL instance name (required)"
    echo "  -d, --db-region REGION         Cloud SQL region (default: us-central1)"
    echo "  -h, --help                     Show this help message"
    echo ""
    echo "Environment variables from .env will be used for configuration."
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -p|--project-id)
            PROJECT_ID="$2"
            shift
            shift
            ;;
        -r|--region)
            REGION="$2"
            shift
            shift
            ;;
        -s|--service-name)
            SERVICE_NAME="$2"
            shift
            shift
            ;;
        -i|--db-instance)
            DB_INSTANCE="$2"
            shift
            shift
            ;;
        -d|--db-region)
            DB_REGION="$2"
            shift
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$PROJECT_ID" ]]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    show_help
    exit 1
fi

if [[ -z "$DB_INSTANCE" ]]; then
    echo -e "${RED}Error: Database instance name is required${NC}"
    show_help
    exit 1
fi

# Set the project
echo -e "${GREEN}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project "${PROJECT_ID}"

# Build the Docker image
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
echo -e "${GREEN}Building and pushing Docker image...${NC}"
gcloud builds submit --tag "${IMAGE_NAME}" .

# Generate a secure secret key if not set in .env
if ! grep -q "^SECRET_KEY=" .env; then
    echo -e "${YELLOW}Generating a new SECRET_KEY...${NC}"
    SECRET_KEY=$(openssl rand -hex 32)
    echo "SECRET_KEY=${SECRET_KEY}" >> .env
fi

# Generate environment variables for deployment
ENV_VARS=(
    "ENVIRONMENT=production"
    "DEBUG=False"
    "DB_HOST=/cloudsql/${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}"
    "DB_PORT=5432"
    "DB_NAME=${DB_NAME:-photo_portfolio}"
    "DB_USER=${DB_USER:-postgres}"
    "DB_PASSWORD=${DB_PASSWORD}"
    "SECRET_KEY=${SECRET_KEY}"
    "ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-1440}"
    "GCS_BUCKET=${GCS_BUCKET}"
    "GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json"
)

# Join environment variables with commas
ENV_VARS_STR=$(IFS=,; echo "${ENV_VARS[*]}")

# Deploy to Cloud Run
echo -e "${GREEN}Deploying to Cloud Run...${NC}"
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --update-env-vars "${ENV_VARS_STR}" \
    --add-cloudsql-instances "${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}" \
    --set-cloudsql-instances "${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}" \
    --cpu 1 \
    --memory 1Gi \
    --min-instances 1 \
    --max-instances 3 \
    --concurrency 80 \
    --timeout 300

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)')
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "Service URL: ${SERVICE_URL}"

# Enable required APIs if not already enabled
echo -e "${GREEN}Enabling required APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    compute.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Don't forget to set up your database and run migrations.${NC}"
