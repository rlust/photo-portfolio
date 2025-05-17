#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
SERVICE_URL=""
BEARER_TOKEN=""

# Function to display help
show_help() {
    echo -e "${YELLOW}Trigger GCS Reindexing for Photo Portfolio${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -u, --url URL            Base URL of the deployed service (e.g., https://your-service.run.app)"
    "  -t, --token TOKEN        Bearer token for authentication (if required)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "This script triggers the GCS reindexing endpoint and verifies the database population."
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -u|--url)
            SERVICE_URL="$2"
            shift
            shift
            ;;
        -t|--token)
            BEARER_TOKEN="$2"
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
if [[ -z "$SERVICE_URL" ]]; then
    echo -e "${RED}Error: Service URL is required${NC}"
    show_help
    exit 1
fi

# Ensure URL doesn't end with a slash
SERVICE_URL=${SERVICE_URL%/}

# Prepare headers
HEADERS=("-H" "Content-Type: application/json")
if [[ -n "$BEARER_TOKEN" ]]; then
    HEADERS+=("-H" "Authorization: Bearer ${BEARER_TOKEN}")
fi

# Function to make HTTP requests with retries
http_request() {
    local url=$1
    local method=${2:-GET}
    local data=${3:-}
    local max_retries=3
    local retry_count=0
    local wait_time=2
    
    while [[ $retry_count -lt $max_retries ]]; do
        if [[ -n "$data" ]]; then
            response=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" "${HEADERS[@]}" -d "$data")
        else
            response=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" "${HEADERS[@]}")
        fi
        
        if [[ "$response" -eq 200 ]] || [[ "$response" -eq 201 ]]; then
            echo "$response"
            return 0
        elif [[ "$response" -eq 401 ]] || [[ "$response" -eq 403 ]]; then
            echo -e "${RED}Error: Authentication failed (HTTP $response)${NC}"
            exit 1
        else
            retry_count=$((retry_count + 1))
            if [[ $retry_count -lt $max_retries ]]; then
                echo -e "${YELLOW}Retrying in ${wait_time}s... (Attempt $((retry_count + 1))/$max_retries)${NC}"
                sleep $wait_time
                wait_time=$((wait_time * 2)) # Exponential backoff
            fi
        fi
    done
    
    echo -e "${RED}Error: Request failed after $max_retries attempts (HTTP $response)${NC}"
    exit 1
}

# Check if service is healthy
echo -e "${GREEN}Checking service health...${NC}"
HEALTH_URL="${SERVICE_URL}/api/health"
http_request "$HEALTH_URL" "GET"
echo -e "${GREEN}Service is healthy${NC}"

# Trigger GCS reindexing
echo -e "${GREEN}Triggering GCS reindexing...${NC}"
REINDEX_URL="${SERVICE_URL}/api/reindex-gcs"
http_request "$REINDEX_URL" "POST" '{"force": true}'
echo -e "${GREEN}GCS reindexing triggered successfully${NC}"

# Verify database population
echo -e "${GREEN}Verifying database population...${NC}"
PHOTOS_URL="${SERVICE_URL}/api/photos"
response=$(http_request "$PHOTOS_URL" "GET")

if [[ -n "$response" ]]; then
    echo -e "${GREEN}Database verification successful${NC}
"
    echo -e "${YELLOW}Reindexing completed successfully!${NC}"
    echo -e "You can now access your photos at: ${PHOTOS_URL}"
else
    echo -e "${YELLOW}Warning: No photos found in the database after reindexing${NC}"
    echo -e "Check the service logs for more information."
fi
