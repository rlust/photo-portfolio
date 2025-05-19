#!/bin/bash

# Exit on error, unset variables, and pipeline errors
set -euo pipefail

# Enable debug mode if DEBUG is set to 1
[[ "${DEBUG:-0}" == "1" ]] && set -x

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Default values
PROJECT_ID=""
INSTANCE_NAME=""
REGION="us-central1"
PORT=5432
CREDENTIALS_FILE="${HOME}/.config/gcloud/application_default_credentials.json"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Function to display help
show_help() {
    echo -e "${YELLOW}Cloud SQL Proxy Manager${NC}"
    echo ""
    echo "This script helps manage the Cloud SQL Proxy for local development."
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --project-id PROJECT_ID     Google Cloud project ID (required)"
    echo "  -i, --instance INSTANCE       Cloud SQL instance name (required)"
    echo "  -r, --region REGION          Cloud SQL region (default: us-central1)"
    echo "  -P, --port PORT              Local port to use (default: 5432)"
    echo "  -c, --credentials FILE       Path to service account key file"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -p my-project -i my-db-instance -r us-central1 -P 5432"
    exit 0
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify required tools are installed
verify_requirements() {
    local missing=()
    
    for cmd in gcloud curl; do
        if ! command_exists "$cmd"; then
            missing+=("$cmd")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "The following required tools are missing: ${missing[*]}"
        exit 1
    fi
}

# Check if Cloud SQL Proxy is installed
check_cloud_sql_proxy() {
    if ! command_exists cloud-sql-proxy; then
        log_warning "Cloud SQL Proxy is not installed. Installing..."
        install_cloud_sql_proxy
    fi
}

# Install Cloud SQL Proxy
install_cloud_sql_proxy() {
    local os_type
    local cloud_sql_proxy_url
    
    # Detect OS type
    case "$(uname -s)" in
        Linux*)     os_type=linux;;
        Darwin*)    os_type=darwin;;
        *)          os_type="UNKNOWN:${unameOut}"
    esac
    
    # Check if the OS is supported
    if [[ "$os_type" != "linux" && "$os_type" != "darwin" ]]; then
        log_error "Unsupported operating system: $os_type"
        exit 1
    fi
    
    # Download and install Cloud SQL Proxy
    local version="v2.8.0"
    local download_url="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/${version}/cloud-sql-proxy.${os_type}.amd64"
    local install_path="/usr/local/bin/cloud-sql-proxy"
    
    log_info "Downloading Cloud SQL Proxy ${version}..."
    
    if ! sudo curl -L "${download_url}" -o "${install_path}"; then
        log_error "Failed to download Cloud SQL Proxy"
        exit 1
    fi
    
    # Make the binary executable
    if ! sudo chmod +x "${install_path}"; then
        log_error "Failed to make Cloud SQL Proxy executable"
        exit 1
    fi
    
    log_success "Cloud SQL Proxy installed successfully to ${install_path}"
}

# Check if port is available
check_port_available() {
    local port=$1
    
    if command_exists lsof; then
        if lsof -i ":${port}" >/dev/null 2>&1; then
            log_error "Port ${port} is already in use. Please choose a different port."
            exit 1
        fi
    elif command_exists netstat; then
        if netstat -tuln | grep -q ":${port} "; then
            log_error "Port ${port} is already in use. Please choose a different port."
            exit 1
        fi
    else
        log_warning "Could not check if port ${port} is in use. Install 'lsof' or 'netstat' for better port checking."
    fi
}

# Start Cloud SQL Proxy
start_cloud_sql_proxy() {
    local instance_connection="${PROJECT_ID}:${REGION}:${INSTANCE_NAME}"
    local credentials_flag=""
    
    # Check if using application default credentials or service account key file
    if [ -n "${CREDENTIALS_FILE}" ] && [ -f "${CREDENTIALS_FILE}" ]; then
        credentials_flag="--credentials-file=${CREDENTIALS_FILE}"
    fi
    
    log_info "Starting Cloud SQL Proxy for instance: ${instance_connection}"
    log_info "Local port: ${PORT}"
    log_info "Using credentials: ${CREDENTIALS_FILE:-Application Default Credentials}"
    
    # Check if port is available
    check_port_available "${PORT}"
    
    # Start Cloud SQL Proxy in the background
    cloud-sql-proxy \
        --port "${PORT}" \
        ${credentials_flag} \
        "${instance_connection}" &
    
    local proxy_pid=$!
    
    # Store the PID in a file for later reference
    echo "${proxy_pid}" > "/tmp/cloud-sql-proxy-${INSTANCE_NAME}.pid"
    
    # Wait for the proxy to start
    sleep 3
    
    if ps -p "${proxy_pid}" > /dev/null; then
        log_success "Cloud SQL Proxy started successfully with PID: ${proxy_pid}"
        log_info "You can now connect to your database at localhost:${PORT}"
        log_info "Press Ctrl+C to stop the proxy"
        
        # Wait for the proxy to finish
        wait "${proxy_pid}" || true
        
        # Clean up PID file
        rm -f "/tmp/cloud-sql-proxy-${INSTANCE_NAME}.pid"
    else
        log_error "Failed to start Cloud SQL Proxy"
        exit 1
    fi
}

# Stop Cloud SQL Proxy
stop_cloud_sql_proxy() {
    local pid_file="/tmp/cloud-sql-proxy-${INSTANCE_NAME}.pid"
    
    if [ -f "${pid_file}" ]; then
        local pid
        pid=$(cat "${pid_file}")
        
        if ps -p "${pid}" > /dev/null; then
            log_info "Stopping Cloud SQL Proxy (PID: ${pid})..."
            kill -TERM "${pid}" || true
            
            # Wait for the process to terminate
            if wait "${pid}" 2>/dev/null; then
                log_success "Cloud SQL Proxy stopped successfully"
            else
                log_warning "Cloud SQL Proxy did not stop gracefully"
            fi
        else
            log_warning "No running Cloud SQL Proxy found with PID: ${pid}"
        fi
        
        # Remove the PID file
        rm -f "${pid_file}"
    else
        log_warning "No PID file found for instance: ${INSTANCE_NAME}"
    fi
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -p|--project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            -i|--instance)
                INSTANCE_NAME="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -P|--port)
                PORT="$2"
                shift 2
                ;;
            -c|--credentials)
                CREDENTIALS_FILE="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                ;;
            --stop)
                STOP_PROXY=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Main function
main() {
    # Verify requirements
    verify_requirements
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Check if help was requested
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    # Check if we should stop the proxy
    if [ "${STOP_PROXY:-false}" = true ]; then
        stop_cloud_sql_proxy
        exit 0
    fi
    
    # Validate required arguments
    if [ -z "$PROJECT_ID" ]; then
        log_error "Project ID is required"
        show_help
        exit 1
    fi
    
    if [ -z "$INSTANCE_NAME" ]; then
        log_error "Instance name is required"
        show_help
        exit 1
    fi
    
    # Check if Cloud SQL Proxy is installed
    check_cloud_sql_proxy
    
    # Start the Cloud SQL Proxy
    start_cloud_sql_proxy
}

# Only run main if this script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
