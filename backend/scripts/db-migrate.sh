#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="photo-portfolio-backend"
MAX_RETRIES=5
RETRY_DELAY=10  # seconds

# Function to display help
show_help() {
    echo -e "${YELLOW}Run database migrations for Photo Portfolio Backend${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --project-id PROJECT_ID  Google Cloud project ID (required)"
    echo "  -r, --region REGION        Google Cloud region (default: us-central1)"
    echo "  -s, --service-name NAME    Service name (default: photo-portfolio-backend)"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "This script will run database migrations on the deployed Cloud Run service."
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

# Set the project
echo -e "${GREEN}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project "${PROJECT_ID}"

# Get the service URL and verify the service exists
echo -e "${BLUE}Getting service URL for ${SERVICE_NAME} in region ${REGION}...${NC}"
SERVICE_URL=""
for i in $(seq 1 $MAX_RETRIES); do
    SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)' 2>/dev/null || true)
    
    if [[ -n "$SERVICE_URL" ]]; then
        break
    fi
    
    if [[ $i -lt $MAX_RETRIES ]]; then
        echo -e "${YELLOW}Service not ready yet, retrying in ${RETRY_DELAY} seconds... (Attempt ${i}/${MAX_RETRIES})${NC}"
        sleep $RETRY_DELAY
    else
        echo -e "${RED}Error: Could not find service ${SERVICE_NAME} in region ${REGION} after ${MAX_RETRIES} attempts${NC}"
        exit 1
    fi
done

echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"

# Get the ID token for authentication
ID_TOKEN=$(gcloud auth print-identity-token)

# Run database migrations
echo -e "${GREEN}Running database migrations...${NC}
"

# Wait for the service to be ready
echo -e "${BLUE}Waiting for the service to be ready...${NC}"
for i in $(seq 1 $MAX_RETRIES); do
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/api/health" 2>/dev/null || true)
    
    if [[ "$HEALTH_RESPONSE" == "200" ]]; then
        HEALTH_JSON=$(curl -s "${SERVICE_URL}/api/health")
        DB_STATUS=$(echo "$HEALTH_JSON" | grep -o '"database":"[^"]*"' | cut -d'"' -f4)
        
        if [[ "$DB_STATUS" == "connected" ]]; then
            echo -e "${GREEN}Service is healthy and database is connected.${NC}"
            break
        else
            echo -e "${YELLOW}Service is up but database is not connected: ${DB_STATUS}${NC}"
        fi
    else
        echo -e "${YELLOW}Health check failed with status code: ${HEALTH_RESPONSE:-N/A}${NC}"
    fi
    
    if [[ $i -lt $MAX_RETRIES ]]; then
        echo -e "${YELLOW}Waiting ${RETRY_DELAY} seconds before retry... (Attempt ${i}/${MAX_RETRIES})${NC}"
        sleep $RETRY_DELAY
    else
        echo -e "${RED}Error: Service health check failed after ${MAX_RETRIES} attempts${NC}"
        exit 1
    fi
done

# Run database migrations
echo -e "\n${BLUE}Running database migrations...${NC}"
MIGRATION_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST -H "Authorization: Bearer ${ID_TOKEN}" "${SERVICE_URL}/api/reset-db" 2>/dev/null || true)
MIGRATION_HTTP_CODE=$(echo "$MIGRATION_RESPONSE" | tail -n1)
MIGRATION_BODY=$(echo "$MIGRATION_RESPONSE" | sed '$d')

if [[ "$MIGRATION_HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}Database migrations completed successfully${NC}"
    echo "Response: $MIGRATION_BODY"
else
    echo -e "${YELLOW}Warning: Database migration request returned HTTP ${MIGRATION_HTTP_CODE}${NC}"
    echo "Response: $MIGRATION_BODY"
fi

# Trigger reindexing of photos in GCS
echo -e "\n${BLUE}Triggering reindexing of photos in GCS...${NC}"
REINDEX_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST -H "Authorization: Bearer ${ID_TOKEN}" "${SERVICE_URL}/api/reindex-gcs" 2>/dev/null || true)
REINDEX_HTTP_CODE=$(echo "$REINDEX_RESPONSE" | tail -n1)
REINDEX_BODY=$(echo "$REINDEX_RESPONSE" | sed '$d')

if [[ "$REINDEX_HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}Reindexing completed successfully${NC}"
    echo "Response: $REINDEX_BODY"
else
    echo -e "${YELLOW}Warning: Reindexing request returned HTTP ${REINDEX_HTTP_CODE}${NC}"
    echo "Response: $REINDEX_BODY"
fi

# Final health check
echo -e "\n${BLUE}Performing final health check...${NC}"
FINAL_HEALTH=$(curl -s "${SERVICE_URL}/api/health")
echo "$FINAL_HEALTH" | jq . 2>/dev/null || echo "$FINAL_HEALTH"

# Get service logs for debugging
echo -e "\n${BLUE}Fetching recent service logs...${NC}" 
SERVICE_LOGS=$(gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
    --limit=20 \
    --format="value(timestamp, severity, jsonPayload.message)" 2>/dev/null || true)

echo -e "${GREEN}Recent logs:${NC}"
echo "$SERVICE_LOGS" | head -n 10

if [[ -n "$SERVICE_LOGS" && $(echo "$SERVICE_LOGS" | wc -l) -gt 10 ]]; then
    echo -e "${YELLOW}... and $(($(echo "$SERVICE_LOGS" | wc -l) - 10)) more lines${NC}"
fi

echo -e "\n${GREEN}Database migrations and reindexing process completed!${NC}"
echo -e "${BLUE}Service URL: ${SERVICE_URL}${NC}"
echo -e "${BLUE}Health Check: ${SERVICE_URL}/api/health${NC}"
echo -e "${BLUE}API Documentation: ${SERVICE_URL}/docs${NC}\n"
