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
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
DB_INSTANCE=""
DB_REGION="us-central1"
ENV_FILE=".env"
SKIP_BUILD=false
SKIP_DEPLOY=false
VERBOSE=false

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
    echo -e "${YELLOW}Deploy Photo Portfolio Backend to Google Cloud Run${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -p, --project-id PROJECT_ID       Google Cloud project ID (required)"
    echo "  -r, --region REGION             Google Cloud region (default: us-central1)"
    echo "  -s, --service NAME              Service name (default: photo-portfolio-backend)"
    echo "  -i, --db-instance INSTANCE      Cloud SQL instance name (required)"
    echo "  -d, --db-region REGION         Cloud SQL region (default: us-central1)"
    echo "  -e, --env-file FILE            Path to .env file (default: .env)"
    echo "  --skip-build                   Skip Docker build step"
    echo "  --skip-deploy                  Skip deployment step"
    echo "  -v, --verbose                  Enable verbose output"
    echo "  -h, --help                     Show this help message"
    echo ""
    echo "Environment variables from the specified .env file will be used for configuration."
    exit 0
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify required tools are installed
verify_requirements() {
    local missing=()
    
    for cmd in gcloud docker openssl; do
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
    
    if [ ! -f "$env_file" ]; then
        log_warning "Environment file $env_file not found. Creating a new one."
        touch "$env_file"
    fi
    
    # Export all variables from .env file
    set -o allexport
    # shellcheck source=/dev/null
    source "$env_file"
    set +o allexport
    
    # Set default values for required variables if not set
    export DB_NAME="${DB_NAME:-photo_portfolio}"
    if [ -z "${DB_USER}" ]; then
    echo "Database user (DB_USER) is required"
    exit 1
fi
if [ "${DB_USER}" = "postgres" ]; then
    echo "Refusing to run with DB_USER=postgres. Use the application user (e.g., rlust)."
    exit 1
fi
export DB_USER="${DB_USER}"
    export DB_PASSWORD="${DB_PASSWORD:-}"
    export GCS_BUCKET="${GCS_BUCKET:-${PROJECT_ID}-photo-portfolio}"
    export ACCESS_TOKEN_EXPIRE_MINUTES="${ACCESS_TOKEN_EXPIRE_MINUTES:-1440}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    
    if [ -z "$DB_PASSWORD" ]; then
        log_warning "DB_PASSWORD is not set in $env_file. A random password will be generated."
        export DB_PASSWORD=$(openssl rand -hex 16)
        echo "DB_PASSWORD=$DB_PASSWORD" >> "$env_file"
    fi
    
    if [ -z "${SECRET_KEY:-}" ]; then
        log_warning "SECRET_KEY is not set in $env_file. A random key will be generated."
        export SECRET_KEY=$(openssl rand -hex 32)
        echo "SECRET_KEY=$SECRET_KEY" >> "$env_file"
    fi
}

# Validate deployment configuration
validate_config() {
    local errors=0
    
    if [ -z "$PROJECT_ID" ]; then
        log_error "Project ID is required"
        errors=$((errors + 1))
    fi
    
    if [ -z "$DB_INSTANCE" ]; then
        log_error "Database instance name is required"
        errors=$((errors + 1))
    fi
    
    if [ -z "$DB_PASSWORD" ]; then
        log_error "Database password is not set"
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -p|--project-id)
            PROJECT_ID="$2"
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
        -i|--db-instance)
            DB_INSTANCE="$2"
            shift 2
            ;;
        -d|--db-region)
            DB_REGION="$2"
            shift 2
            ;;
        -e|--env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-deploy)
            SKIP_DEPLOY=true
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
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Verify required tools are installed
verify_requirements

# Load environment variables
load_env "$ENV_FILE"

# Set the project
log_info "Setting project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}" --verbosity=${VERBOSE:+debug}

# Build and push the Docker image if not skipped
if [ "$SKIP_BUILD" = false ]; then
    log_info "Building and pushing Docker image..."
    gcloud builds submit \
        --tag "${IMAGE_NAME}" \
        --timeout "30m" \
        --verbosity ${VERBOSE:+debug} \
        .
    log_success "Docker image built and pushed successfully"
else
    log_warning "Skipping Docker build as requested"
fi

# Set default values for required variables if not set
export DB_NAME="${DB_NAME:-photo_portfolio}"
if [ -z "${DB_USER}" ]; then
    echo "Database user (DB_USER) is required"
    exit 1
fi
if [ "${DB_USER}" = "postgres" ]; then
    echo "Refusing to run with DB_USER=postgres. Use the application user (e.g., rlust)."
    exit 1
fi
export DB_USER="${DB_USER}"

# Generate a secure secret key if not set
if [ -z "${SECRET_KEY:-}" ]; then
    log_warning "SECRET_KEY is not set. Generating a new one..."
    export SECRET_KEY=$(openssl rand -hex 32)
    echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
fi

# Validate configuration
validate_config

# Generate environment variables for deployment
ENV_VARS=(
    # Application settings
    "ENVIRONMENT=production"
    "DEBUG=False"
    "LOG_LEVEL=${LOG_LEVEL:-INFO}"
    
    # Database settings
    "DB_HOST=/cloudsql/${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}"
    "DB_PORT=5432"
    "DB_NAME=${DB_NAME}"
    "DB_USER=${DB_USER}"
    "DB_PASSWORD=${DB_PASSWORD}"
    "CLOUD_SQL_CONNECTION_NAME=${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}"
    
    # Security
    "SECRET_KEY=${SECRET_KEY}"
    "ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES}"
    
    # Google Cloud
    "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
    "GCS_BUCKET=${GCS_BUCKET}"
    "GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json"
    
    # Performance
    "WORKERS_PER_CORE=1"
    "MAX_WORKERS=4"
    "WEB_CONCURRENCY=4"
    "TIMEOUT=120"
    "KEEP_ALIVE=5"
    
    # CORS (adjust as needed)
    "CORS_ORIGINS=['*']"
    "CORS_METHODS=['*']"
    "CORS_HEADERS=['*']"
    
    # Security headers (enable in production)
    "SECURE_SSL_REDIRECT=True"
    "SESSION_COOKIE_SECURE=True"
    "CSRF_COOKIE_SECURE=True"
    "SECURE_BROWSER_XSS_FILTER=True"
    "SECURE_CONTENT_TYPE_NOSNIFF=True"
    "X_FRAME_OPTIONS=DENY"
    "SECURE_HSTS_SECONDS=31536000"
    "SECURE_HSTS_INCLUDE_SUBDOMAINS=True"
    "SECURE_HSTS_PRELOAD=True"
    "SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https')"
)

# Add database URL for SQLAlchemy
DB_URL="postgresql+pg8000://${DB_USER}:${DB_PASSWORD}@/db?unix_sock=/cloudsql/${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}/.s.PGSQL.5432"
ENV_VARS+=("DATABASE_URL=${DB_URL}")

# Join environment variables with commas
ENV_VARS_STR=$(IFS=,; echo "${ENV_VARS[*]}")

# Deploy to Cloud Run
if [ "$SKIP_DEPLOY" = false ]; then
    log_info "Deploying ${SERVICE_NAME} to Cloud Run in ${REGION}..."
    
    # Enable required APIs if not already enabled
    log_info "Enabling required Google Cloud APIs..."
    gcloud services enable \
        run.googleapis.com \
        sql-component.googleapis.com \
        sqladmin.googleapis.com \
        compute.googleapis.com \
        containerregistry.googleapis.com \
        cloudbuild.googleapis.com \
        cloudkms.googleapis.com \
        iam.googleapis.com \
        --project "${PROJECT_ID}" \
        --verbosity ${VERBOSE:+debug}

    # Deploy the service
    log_info "Deploying Cloud Run service..."
    gcloud run deploy "${SERVICE_NAME}" \
        --image "${IMAGE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --allow-unauthenticated \
        --update-env-vars "${ENV_VARS_STR}" \
        --add-cloudsql-instances "${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}" \
        --set-cloudsql-instances "${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}" \
        --cpu 1 \
        --memory "2Gi" \
        --min-instances 1 \
        --max-instances 3 \
        --concurrency 80 \
        --timeout 300 \
        --ingress all \
        --vpc-egress all \
        --set-env-vars "CLOUD_SQL_INSTANCE=${PROJECT_ID}:${DB_REGION}:${DB_INSTANCE}" \
        --no-use-http2 \
        --verbosity ${VERBOSE:+debug} \
        --format "value(status.url)" \
        --quiet
    
    log_success "Cloud Run service deployed successfully"
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --format 'value(status.url)' \
        --verbosity ${VERBOSE:+debug})
    
    log_info "Service URL: ${SERVICE_URL}"
    
    # Configure IAM permissions
    configure_iam_permissions
    
    # Run database migrations
    run_database_migrations
    
    log_success "Deployment completed successfully!"
    log_info "Service URL: ${SERVICE_URL}"
    log_info "API Health Check: ${SERVICE_URL}/api/health"
else
    log_warning "Skipping deployment as requested"
fi

# Configure IAM permissions for the service
configure_iam_permissions() {
    log_info "Configuring IAM permissions..."
    
    # Get the Cloud Run service account email
    local service_account_email
    service_account_email=$(gcloud run services describe "${SERVICE_NAME}" \
        --platform managed \
        --region "${REGION}" \
        --format 'value(spec.template.spec.serviceAccountName)' \
        --verbosity ${VERBOSE:+debug} || true)
    
    if [ -z "$service_account_email" ]; then
        # If no service account is found, use the default Compute Engine service account
        local project_number
        project_number=$(gcloud projects describe "${PROJECT_ID}" \
            --format 'value(projectNumber)' \
            --verbosity ${VERBOSE:+debug})
        service_account_email="${project_number}-compute@developer.gserviceaccount.com"
        log_warning "Using default service account: ${service_account_email}"
    fi
    
    # Add IAM policy bindings
    declare -A roles=(
        ["roles/cloudsql.client"]="Cloud SQL Client"
        ["roles/storage.objectAdmin"]="Storage Object Admin"
        ["roles/logging.logWriter"]="Log Writer"
        ["roles/monitoring.metricWriter"]="Monitoring Metric Writer"
        ["roles/errorreporting.writer"]="Error Reporting Writer"
    )
    
    for role in "${!roles[@]}"; do
        log_info "Adding ${roles[$role]} role to ${service_account_email}..."
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${service_account_email}" \
            --role="${role}" \
            --verbosity ${VERBOSE:+debug} >/dev/null || true
    done
    
    log_success "IAM permissions configured successfully"
}

# Run database migrations
run_database_migrations() {
    log_info "Running database migrations..."
    
    # Check if migrations directory exists
    if [ ! -d "migrations" ]; then
        log_warning "Migrations directory not found. Initializing Alembic..."
        alembic init migrations || {
            log_error "Failed to initialize Alembic"
            return 1
        }
    fi
    
    # Run migrations
    alembic upgrade head || {
        log_error "Database migration failed"
        return 1
    }
    
    log_success "Database migrations completed successfully"
}

# Main execution
main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    # Load environment
    load_env "$ENV_FILE"
    
    # Build and deploy
    if [ "$SKIP_BUILD" = false ]; then
        build_docker_image
    fi
    
    if [ "$SKIP_DEPLOY" = false ]; then
        deploy_to_cloud_run
    fi
    
    log_success "Deployment process completed!"
}

# Only run main if this script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
