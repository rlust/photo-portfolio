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
REGION="us-central1"
SERVICE_NAME="photo-portfolio-backend"
DB_INSTANCE=""
DB_NAME="photo_portfolio"
DB_USER="postgres"
DB_PASSWORD=""
LOCAL_PORT=5432
ENV_FILE=".env"
VERBOSE=false
SKIP_PROXY=false

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
    echo -e "${YELLOW}Photo Portfolio Database Administration Tool${NC}"
    echo ""
    echo "This script helps manage database operations for the Photo Portfolio application."
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  migrate         Run database migrations"
    echo "  reindex         Reindex photos in Google Cloud Storage"
    echo "  connect         Connect to the database using psql"
    echo "  dump            Create a database dump"
    echo "  restore         Restore a database from a dump"
    echo "  reset           Reset the database (drop and recreate)"
    echo "  help            Show this help message"
    echo ""
    echo "Options:"
    echo "  -p, --project-id PROJECT_ID     Google Cloud project ID (required for remote operations)"
    echo "  -i, --instance INSTANCE       Cloud SQL instance name (required for remote operations)"
    echo "  -r, --region REGION           Google Cloud region (default: us-central1)"
    echo "  -s, --service NAME            Service name (default: photo-portfolio-backend)"
    echo "  -d, --db-name NAME            Database name (default: photo_portfolio)"
    echo "  -u, --user USER               Database user (default: postgres)"
    echo "  -w, --password PASSWORD       Database password"
    echo "  -P, --port PORT               Local port for database connection (default: 5432)"
    echo "  -e, --env-file FILE           Path to .env file (default: .env)"
    echo "  --skip-proxy                  Skip starting Cloud SQL Proxy (assumes it's already running)"
    echo "  -v, --verbose                 Enable verbose output"
    echo "  -h, --help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Run migrations locally"
    echo "  $0 migrate -p my-project -i my-db-instance"
    echo ""
    echo "  # Reindex photos in production"
    echo "  $0 reindex -p my-project -i my-db-instance"
    echo ""
    echo "  # Connect to the database"
    echo "  $0 connect -p my-project -i my-db-instance"
    exit 0
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify required tools are installed
verify_requirements() {
    local missing=()
    
    for cmd in gcloud psql pg_dump pg_restore; do
        if ! command_exists "$cmd"; then
            missing+=("$cmd")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "The following required tools are missing: ${missing[*]}"
        exit 1
    fi
}

# Load environment variables from .env file
load_env() {
    local env_file="${1:-.env}"
    
    if [ -f "$env_file" ]; then
        # Export all variables from .env file
        set -o allexport
        # shellcheck source=/dev/null
        source "$env_file"
        set +o allexport
        
        # Set default values for required variables if not set
        export DB_NAME="${DB_NAME:-photo_portfolio}"
        if [ -z "${DB_USER}" ]; then
    log_error "Database user (DB_USER) is required"
    exit 1
fi
if [ "${DB_USER}" = "postgres" ]; then
    log_error "Refusing to run with DB_USER=postgres. Use the application user (e.g., rlust)."
    exit 1
fi
export DB_USER="${DB_USER}"
        export DB_PASSWORD="${DB_PASSWORD:-}"

        # Safety check: refuse to run as superuser
        if [ -z "${DB_USER}" ]; then
            log_error "Database user (DB_USER) is required"
            exit 1
        fi
        if [ "${DB_USER}" = "postgres" ]; then
            log_error "Refusing to run with DB_USER=postgres. Use the application user (e.g., rlust)."
            exit 1
        fi

        export DB_HOST="${DB_HOST:-localhost}"
        export DB_PORT="${DB_PORT:-5432}"
    else
        log_warning "Environment file $env_file not found. Using command line arguments."
    fi
}

# Start Cloud SQL Proxy
start_cloud_sql_proxy() {
    if [ "$SKIP_PROXY" = true ]; then
        log_info "Skipping Cloud SQL Proxy start as requested"
        return 0
    fi
    
    log_info "Starting Cloud SQL Proxy..."
    
    # Check if the proxy is already running
    if pgrep -f "cloud-sql-proxy.*${PROJECT_ID}:${REGION}:${DB_INSTANCE}" > /dev/null; then
        log_info "Cloud SQL Proxy is already running"
        return 0
    fi
    
    # Start the proxy in the background
    nohup cloud-sql-proxy \
        --port "${LOCAL_PORT}" \
        "${PROJECT_ID}:${REGION}:${DB_INSTANCE}" > /tmp/cloud-sql-proxy.log 2>&1 &
    
    # Store the PID
    CLOUD_SQL_PROXY_PID=$!
    
    # Wait for the proxy to start
    sleep 3
    
    if ps -p "${CLOUD_SQL_PROXY_PID}" > /dev/null; then
        log_success "Cloud SQL Proxy started with PID: ${CLOUD_SQL_PROXY_PID}"
        # Set a trap to stop the proxy when the script exits
        trap 'stop_cloud_sql_proxy' EXIT
    else
        log_error "Failed to start Cloud SQL Proxy"
        cat /tmp/cloud-sql-proxy.log >&2 || true
        exit 1
    fi
}

# Stop Cloud SQL Proxy
stop_cloud_sql_proxy() {
    if [ -n "${CLOUD_SQL_PROXY_PID:-}" ]; then
        log_info "Stopping Cloud SQL Proxy (PID: ${CLOUD_SQL_PROXY_PID})..."
        kill -TERM "${CLOUD_SQL_PROXY_PID}" 2>/dev/null || true
        wait "${CLOUD_SQL_PROXY_PID}" 2>/dev/null || true
        log_success "Cloud SQL Proxy stopped"
    fi
}

# Get the Cloud Run service URL
get_service_url() {
    gcloud run services describe "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --format 'value(status.url)' \
        --verbosity ${VERBOSE:+debug}
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    if [ -z "${DB_PASSWORD}" ]; then
        log_error "Database password is required"
        exit 1
    fi
    
    # Check if using Cloud SQL Proxy or direct connection
    if [ -n "${PROJECT_ID}" ] && [ -n "${DB_INSTANCE}" ]; then
        start_cloud_sql_proxy
        local db_host="localhost"
        local db_port="${LOCAL_PORT}"
    else
        local db_host="${DB_HOST}"
        local db_port="${DB_PORT}"
    fi
    
    # Set the DATABASE_URL environment variable for Alembic
    export DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@${db_host}:${db_port}/${DB_NAME}"
    
    # Run migrations
    if ! alembic upgrade head; then
        log_error "Database migration failed"
        return 1
    fi
    
    log_success "Database migrations completed successfully"
}

# Reindex photos in Google Cloud Storage
reindex_photos() {
    log_info "Starting photo reindexing..."
    
    # Get the service URL
    local service_url
    service_url=$(get_service_url)
    
    if [ -z "${service_url}" ]; then
        log_error "Failed to get service URL. Is the service deployed?"
        return 1
    fi
    
    log_info "Service URL: ${service_url}"
    
    # Get an authentication token
    local token
    token=$(gcloud auth print-identity-token --audience="${service_url}")
    
    if [ -z "${token}" ]; then
        log_error "Failed to get authentication token"
        return 1
    fi
    
    # Trigger the reindexing endpoint
    log_info "Triggering reindexing endpoint..."
    
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "Authorization: Bearer ${token}" \
        "${service_url}/api/reindex-gcs")
    
    if [ "${response}" = "200" ] || [ "${response}" = "202" ]; then
        log_success "Reindexing started successfully"
        log_info "Check the application logs for progress"
    else
        log_error "Failed to start reindexing. HTTP status: ${response}"
        return 1
    fi
}

# Connect to the database
connect_to_database() {
    log_info "Connecting to database..."
    
    if [ -z "${DB_PASSWORD}" ]; then
        log_error "Database password is required"
        exit 1
    fi
    
    # Check if using Cloud SQL Proxy or direct connection
    if [ -n "${PROJECT_ID}" ] && [ -n "${DB_INSTANCE}" ]; then
        start_cloud_sql_proxy
        local db_host="localhost"
        local db_port="${LOCAL_PORT}"
    else
        local db_host="${DB_HOST}"
        local db_port="${DB_PORT}"
    fi
    
    # Connect to the database
    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}"
}

# Create a database dump
create_dump() {
    local output_file="${1:-db_dump_$(date +%Y%m%d_%H%M%S).sql}"
    
    log_info "Creating database dump to ${output_file}..."
    
    if [ -z "${DB_PASSWORD}" ]; then
        log_error "Database password is required"
        exit 1
    fi
    
    # Check if using Cloud SQL Proxy or direct connection
    if [ -n "${PROJECT_ID}" ] && [ -n "${DB_INSTANCE}" ]; then
        start_cloud_sql_proxy
        local db_host="localhost"
        local db_port="${LOCAL_PORT}"
    else
        local db_host="${DB_HOST}"
        local db_port="${DB_PORT}"
    fi
    
    # Create the dump
    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        -Fc \
        -f "${output_file}" \
        --no-owner \
        --no-privileges
    
    log_success "Database dump created: ${output_file}"
}

# Restore a database from a dump
restore_dump() {
    local input_file="$1"
    
    if [ ! -f "${input_file}" ]; then
        log_error "Input file not found: ${input_file}"
        exit 1
    fi
    
    log_info "Restoring database from ${input_file}..."
    
    if [ -z "${DB_PASSWORD}" ]; then
        log_error "Database password is required"
        exit 1
    fi
    
    # Check if using Cloud SQL Proxy or direct connection
    if [ -n "${PROJECT_ID}" ] && [ -n "${DB_INSTANCE}" ]; then
        start_cloud_sql_proxy
        local db_host="localhost"
        local db_port="${LOCAL_PORT}"
    else
        local db_host="${DB_HOST}"
        local db_port="${DB_PORT}"
    fi
    
    # Drop and recreate the database
    log_warning "This will drop and recreate the database. Are you sure? [y/N]"
    read -r confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled"
        exit 0
    fi
    
    # Terminate all connections to the database
    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "postgres" \
        -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${DB_NAME}' AND pid <> pg_backend_pid();"
    
    # Drop and recreate the database
    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "postgres" \
        -c "DROP DATABASE IF EXISTS \"${DB_NAME}";"
    
    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "postgres" \
        -c "CREATE DATABASE \"${DB_NAME}";"
    
    # Restore the dump
    PGPASSWORD="${DB_PASSWORD}" pg_restore \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --clean \
        --no-owner \
        --no-privileges \
        "${input_file}"
    
    log_success "Database restored from ${input_file}"
}

# Reset the database (drop and recreate)
reset_database() {
    log_warning "This will DROP and RECREATE the database. Are you sure? [y/N]"
    read -r confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled"
        exit 0
    fi
    
    log_info "Resetting database..."
    
    if [ -z "${DB_PASSWORD}" ]; then
        log_error "Database password is required"
        exit 1
    fi
    
    # Check if using Cloud SQL Proxy or direct connection
    if [ -n "${PROJECT_ID}" ] && [ -n "${DB_INSTANCE}" ]; then
        start_cloud_sql_proxy
        local db_host="localhost"
        local db_port="${LOCAL_PORT}"
    else
        local db_host="${DB_HOST}"
        local db_port="${DB_PORT}"
    fi
    
    # Terminate all connections to the database
    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "postgres" \
        -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${DB_NAME}' AND pid <> pg_backend_pid();"
    
    # Drop and recreate the database
    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "postgres" \
        -c "DROP DATABASE IF EXISTS \"${DB_NAME}";"
    
    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${DB_USER}" \
        -d "postgres" \
        -c "CREATE DATABASE \"${DB_NAME}";"
    
    log_success "Database reset successfully"
    
    # Run migrations if requested
    if [ "${RUN_MIGRATIONS:-false}" = true ]; then
        run_migrations
    fi
}

# Parse command line arguments
parse_arguments() {
    # First argument is the command
    if [ $# -eq 0 ]; then
        show_help
        exit 1
    fi
    
    local command="$1"
    shift
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -p|--project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            -i|--instance)
                DB_INSTANCE="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -s|--service)
                SERVICE_NAME="$2"
                shift 2
                ;;
            -d|--db-name)
                DB_NAME="$2"
                shift 2
                ;;
            -u|--user)
                DB_USER="$2"
                shift 2
                ;;
            -w|--password)
                DB_PASSWORD="$2"
                shift 2
                ;;
            -P|--port)
                LOCAL_PORT="$2"
                shift 2
                ;;
            -e|--env-file)
                ENV_FILE="$2"
                shift 2
                ;;
            --skip-proxy)
                SKIP_PROXY=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                set -x
                shift
                ;;
            -h|--help)
                show_help
                ;;
            --run-migrations)
                RUN_MIGRATIONS=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Execute the command
    case "$command" in
        migrate)
            run_migrations
            ;;
        reindex)
            reindex_photos
            ;;
        connect)
            connect_to_database
            ;;
        dump)
            create_dump "$@"
            ;;
        restore)
            if [ $# -lt 1 ]; then
                log_error "Input file is required for restore"
                show_help
                exit 1
            fi
            restore_dump "$1"
            ;;
        reset)
            reset_database
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Main function
main() {
    # Verify requirements
    verify_requirements
    
    # Load environment variables
    load_env "$ENV_FILE"
    
    # Parse command line arguments
    parse_arguments "$@"
}

# Only run main if this script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
