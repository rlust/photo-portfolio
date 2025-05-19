#!/bin/bash

# Exit on error and unset variables
set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

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

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify required tools are installed
verify_requirements() {
    local missing=()
    
    for cmd in gcloud psql pg_dump curl; do
        if ! command_exists "$cmd"; then
            missing+=("$cmd")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "The following required tools are missing: ${missing[*]}"
        exit 1
    fi
}

# Test Cloud SQL Proxy
test_cloud_sql_proxy() {
    log_info "Testing Cloud SQL Proxy..."
    
    # Start the proxy in the background
    log_info "Starting Cloud SQL Proxy..."
    nohup ./cloud-sql-proxy.sh -p "${PROJECT_ID}" -i "${DB_INSTANCE}" -r "${REGION}" > /tmp/cloud-sql-proxy-test.log 2>&1 &
    local proxy_pid=$!
    
    # Wait for the proxy to start
    sleep 5
    
    # Check if the proxy is running
    if ! ps -p "${proxy_pid}" > /dev/null; then
        log_error "Failed to start Cloud SQL Proxy"
        cat /tmp/cloud-sql-proxy-test.log >&2 || true
        return 1
    fi
    
    log_success "Cloud SQL Proxy started with PID: ${proxy_pid}"
    
    # Test database connection
    log_info "Testing database connection..."
    if PGPASSWORD="${DB_PASSWORD}" psql -h localhost -p 5432 -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1" > /dev/null 2>&1; then
        log_success "Successfully connected to the database"
    else
        log_error "Failed to connect to the database"
        kill -TERM "${proxy_pid}" 2>/dev/null || true
        return 1
    fi
    
    # Stop the proxy
    log_info "Stopping Cloud SQL Proxy..."
    kill -TERM "${proxy_pid}" 2>/dev/null || true
    wait "${proxy_pid}" 2>/dev/null || true
    
    log_success "Cloud SQL Proxy test completed successfully"
}

# Test database migrations
test_migrations() {
    log_info "Testing database migrations..."
    
    # Run migrations
    if ! ./db-admin.sh migrate -p "${PROJECT_ID}" -i "${DB_INSTANCE}" -r "${REGION}" -d "${DB_NAME}" -u "${DB_USER}" -w "${DB_PASSWORD}"; then
        log_error "Database migrations failed"
        return 1
    fi
    
    log_success "Database migrations test completed successfully"
}

# Test database dump and restore
test_dump_restore() {
    log_info "Testing database dump and restore..."
    
    local dump_file="/tmp/test_dump_$(date +%Y%m%d_%H%M%S).sql"
    
    # Create a dump
    log_info "Creating database dump..."
    if ! ./db-admin.sh dump -p "${PROJECT_ID}" -i "${DB_INSTANCE}" -r "${REGION}" -d "${DB_NAME}" -u "${DB_USER}" -w "${DB_PASSWORD}" "${dump_file}"; then
        log_error "Failed to create database dump"
        return 1
    fi
    
    # Restore the dump to a temporary database
    local temp_db="test_restore_$(date +%Y%m%d%H%M%S)"
    
    log_info "Creating temporary database: ${temp_db}"
    if ! PGPASSWORD="${DB_PASSWORD}" psql -h localhost -p 5432 -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${temp_db}\"" ; then
        log_error "Failed to create temporary database"
        return 1
    fi
    
    log_info "Restoring database dump to ${temp_db}..."
    if ! PGPASSWORD="${DB_PASSWORD}" psql -h localhost -p 5432 -U "${DB_USER}" -d "${temp_db}" -f "${dump_file}"; then
        log_error "Failed to restore database dump"
        PGPASSWORD="${DB_PASSWORD}" psql -h localhost -p 5432 -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${temp_db}\"" || true
        return 1
    fi
    
    # Clean up
    log_info "Cleaning up..."
    PGPASSWORD="${DB_PASSWORD}" psql -h localhost -p 5432 -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${temp_db}\"" || true
    rm -f "${dump_file}"
    
    log_success "Database dump and restore test completed successfully"
}

# Main function
main() {
    # Verify requirements
    verify_requirements
    
    # Set default values
    local ENV_FILE="${ENV_FILE:-.env}"
    
    # Load environment variables
    if [ -f "${ENV_FILE}" ]; then
        log_info "Loading environment variables from ${ENV_FILE}"
        # shellcheck source=/dev/null
        source "${ENV_FILE}"
    fi
    
    # Set default values if not provided
    PROJECT_ID="${PROJECT_ID:-}"
    DB_INSTANCE="${DB_INSTANCE:-}"
    DB_NAME="${DB_NAME:-photo_portfolio}"
    DB_USER="${DB_USER:-postgres}"
    DB_PASSWORD="${DB_PASSWORD:-}"
    REGION="${REGION:-us-central1}"
    ENV_FILE="${ENV_FILE:-.env}"
    
    # Check for required variables
    if [ -z "${PROJECT_ID}" ] || [ -z "${DB_INSTANCE}" ] || [ -z "${DB_PASSWORD}" ]; then
        log_error "Missing required environment variables. Please set PROJECT_ID, DB_INSTANCE, and DB_PASSWORD."
        exit 1
    fi
    
    # Run tests
    local tests_passed=0
    local tests_failed=0
    
    # Test Cloud SQL Proxy
    if test_cloud_sql_proxy; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Test database migrations
    if test_migrations; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Test database dump and restore
    if test_dump_restore; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Print summary
    echo -e "\n${GREEN}Tests completed:${NC}"
    echo -e "${GREEN}✓ Passed: ${tests_passed}${NC}"
    
    if [ ${tests_failed} -gt 0 ]; then
        echo -e "${RED}✗ Failed: ${tests_failed}${NC}"
        exit 1
    else
        echo -e "${GREEN}All tests passed successfully!${NC}"
    fi
}

# Only run main if this script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
