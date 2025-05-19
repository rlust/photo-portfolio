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
TIMEOUT=300  # 5 minutes
INTERVAL=10  # 10 seconds

# Function to display help
show_help() {
    echo -e "${YELLOW}Verify Photo Portfolio Deployment${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -u, --url URL            Base URL of the deployed service (e.g., https://your-service.run.app)"
    echo "  -t, --token TOKEN        Bearer token for authentication (if required)"
    echo "  -T, --timeout SECONDS    Maximum time to wait in seconds (default: 300)"
    echo "  -i, --interval SECONDS   Interval between checks in seconds (default: 10)"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "This script verifies that the service is running and the database is properly populated."
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
        -T|--timeout)
            TIMEOUT="$2"
            shift
            shift
            ;;
        -i|--interval)
            INTERVAL="$2"
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

# Function to make HTTP requests
http_request() {
    local url=$1
    local method=${2:-GET}
    local data=${3:-}
    
    if [[ -n "$data" ]]; then
        curl -s -X "$method" "$url" "${HEADERS[@]}" -d "$data"
    else
        curl -s -X "$method" "$url" "${HEADERS[@]}"
    fi
}

# Function to check if service is healthy
check_health() {
    local url="${SERVICE_URL}/api/health"
    local response
    
    response=$(http_request "$url" "GET")
    local status=$(echo "$response" | jq -r '.status' 2>/dev/null || echo "")
    
    if [[ "$status" == "ok" ]]; then
        echo "OK"
    else
        echo "ERROR"
    fi
}

# Function to check database population
check_database() {
    local url="${SERVICE_URL}/api/photos/count"
    local response
    
    response=$(http_request "$url" "GET" 2>/dev/null || echo "")
    local count=$(echo "$response" | jq -r '.count' 2>/dev/null || echo "0")
    
    if [[ -n "$count" && "$count" -gt 0 ]]; then
        echo "$count"
    else
        echo "0"
    fi
}

# Wait for service to be healthy
echo -e "${YELLOW}Waiting for service to be healthy...${NC}"
start_time=$(date +%s)
timeout_time=$((start_time + TIMEOUT))

while [[ $(date +%s) -lt $timeout_time ]]; do
    status=$(check_health)
    
    if [[ "$status" == "OK" ]]; then
        echo -e "${GREEN}Service is healthy!${NC}"
        break
    fi
    
    echo -n "."
    sleep $INTERVAL
done

if [[ "$status" != "OK" ]]; then
    echo -e "\n${RED}Error: Service did not become healthy within ${TIMEOUT} seconds${NC}"
    exit 1
fi

# Check database population
echo -e "${YELLOW}Checking database population...${NC}"
photo_count=$(check_database)

if [[ "$photo_count" -gt 0 ]]; then
    echo -e "${GREEN}Database contains ${photo_count} photos${NC}"
else
    echo -e "${YELLOW}No photos found in the database${NC}"
    echo -e "${YELLOW}You may need to trigger the reindexing process${NC}"
    
    read -p "Would you like to trigger GCS reindexing now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Triggering GCS reindexing...${NC}"
        ./scripts/reindex_gcs.sh --url "$SERVICE_URL" ${BEARER_TOKEN:+"--token $BEARER_TOKEN"}
        
        # Wait a bit for reindexing to complete
        echo -e "${YELLOW}Waiting for reindexing to complete...${NC}"
        sleep 30
        
        # Check database again
        photo_count=$(check_database)
        if [[ "$photo_count" -gt 0 ]]; then
            echo -e "${GREEN}Reindexing successful! Database now contains ${photo_count} photos${NC}"
        else
            echo -e "${YELLOW}No photos found after reindexing. Please check the logs.${NC}"
        fi
    fi
fi

# Final status
echo -e "\n${GREEN}Verification complete!${NC}"
echo -e "Service URL: ${SERVICE_URL}"
echo -e "API Documentation: ${SERVICE_URL}/docs"

if [[ "$photo_count" -gt 0 ]]; then
    echo -e "${GREEN}✅ Deployment is healthy and database contains ${photo_count} photos${NC}"
else
    echo -e "${YELLOW}⚠️  Deployment is healthy but no photos were found in the database${NC}"
    echo -e "   You may need to upload photos or check the reindexing process."
fi
