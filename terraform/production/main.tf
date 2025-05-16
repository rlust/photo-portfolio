# Configure the default provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
  
  # Add retry logic for transient errors
  retry_policy {
    retry_codes    = [429, 500, 502, 503, 504]
    initial_retry_delay_seconds = 1
    max_retry_delay_seconds      = 30
    retry_delay_multiplier       = 2
    max_attempts                 = 5
  }
}

# Create a random ID for unique resource naming
resource "random_id" "suffix" {
  byte_length = 4
}

# Create VPC with secure network architecture
module "vpc" {
  source = "../modules/vpc"

  project_id    = var.project_id
  environment   = var.environment
  vpc_name      = "${var.environment}-vpc"
  region        = var.region
  subnet_cidr   = var.subnet_cidr
  
  # Restrict SSH access to specific IPs
  allowed_ssh_ips = concat(
    var.allowed_ssh_ips,
    # Add any additional IPs that need SSH access
    []
  )
  
  # Enable VPC Flow Logs for security monitoring
  enable_flow_logs = true
  
  # Configure private Google Access for private GKE clusters
  private_ip_google_access = true
  
  # Enable DNS for private zones
  enable_private_dns_zone = true
  
  # Configure logging for firewall rules
  firewall_log_config = {
    metadata = "INCLUDE_ALL_METADATA"
  }
  
  # Add tags for better resource management
  tags = merge(
    local.common_tags,
    {
      Component = "network"
      ManagedBy = "terraform"
    }
  )
}

# Create Cloud SQL instance with high availability and security
module "cloud_sql" {
  source = "../modules/cloud_sql"

  project_id        = var.project_id
  region            = var.region
  zone              = var.zone
  
  # Naming and identifiers
  instance_name     = "${var.environment}-sql-${random_id.suffix.hex}"
  database_name     = var.database_name
  user_name         = var.database_user
  
  # Security
  user_password     = var.database_password
  require_ssl       = true  # Enforce SSL connections
  
  # High availability
  availability_type = "REGIONAL"
  
  # Performance
  tier              = var.database_tier
  disk_size         = var.database_disk_size
  disk_autoresize   = true
  disk_autoresize_limit = 500  # GB
  
  # Maintenance and updates
  maintenance_window = {
    day          = 7  # Sunday
    hour         = 3   # 3 AM UTC
    update_track = "stable"
  }
  
  # Backup configuration
  backup_configuration = {
    enabled            = true
    start_time         = "04:00"  # 4 AM UTC
    location           = var.region
    binary_log_enabled = true     # Point-in-time recovery
    retention_count    = 7        # Keep 7 days of backups
  }
  
  # Network
  vpc_network       = module.vpc.vpc_self_link
  
  # Database flags for performance
  database_flags = [
    {
      name  = "max_connections"
      value = "400"
    },
    {
      name  = "work_mem"
      value = "8192"  # 8MB
    }
  ]
  
  # Monitoring and logging
  enable_slow_query_log = true
  slow_query_log_flags = {
    "log_min_duration_statement" = "1000"  # Log queries slower than 1s
    "log_checkpoints"           = "on"
    "log_connections"           = "on"
    "log_disconnections"        = "on"
    "log_lock_waits"            = "on"
    "log_temp_files"            = "0"     # Log all temp files
  }
  
  # Add tags for better resource management
  tags = merge(
    local.common_tags,
    {
      Component = "database"
      ManagedBy = "terraform"
    }
  )
}

# Create Cloud Storage bucket with security best practices
module "cloud_storage" {
  source = "../modules/cloud_storage"

  
  # Basic configuration
  project_id  = var.project_id
  bucket_name = "${var.project_id}-${var.environment}-${random_id.suffix.hex}"
  location    = var.region
  
  # Versioning and protection
  versioning_enabled = true
  force_destroy      = false  # Prevent accidental deletion in production
  
  # Encryption
  encryption = {
    default_kms_key_name = null  # Use Google-managed encryption key
  }
  
  # IAM
  service_account_email = google_service_account.app.email
  
  # CORS configuration for web access
  cors = [
    {
      origin          = ["https://${var.domain_name}", "http://localhost:3000"]
      method          = ["GET", "HEAD", "PUT", "POST", "DELETE", "OPTIONS"]
      response_header = ["Content-Type", "Content-MD5", "Content-Disposition"]
      max_age_seconds = 3600
    }
  ]
  
  # Lifecycle rules for cost optimization
  lifecycle_rules = [
    # Delete incomplete multipart uploads after 1 day
    {
      action = {
        type = "Delete"
      }
      condition = {
        age                   = 1
        matches_storage_class = ["STANDARD", "NEARLINE", "COLDLINE", "ARCHIVE"]
        with_state            = "INCOMPLETE"
      }
    },
    # Transition to Nearline after 30 days
    {
      action = {
        type          = "SetStorageClass"
        storage_class = "NEARLINE"
      }
      condition = {
        age                   = 30
        matches_storage_class = ["STANDARD"]
      }
    },
    # Delete non-current versions after 90 days
    {
      action = {
        type = "Delete"
      }
      condition = {
        age                   = 90
        num_newer_versions   = 1
        with_state           = "ANY"
      }
    }
  ]
  
  # Uniform bucket-level access (recommended)
  uniform_bucket_level_access = true
  
  # Public access prevention
  public_access_prevention = "enforced"
  
  # Logging
  logging = {
    log_bucket = "${var.project_id}-${var.environment}-logs"
  }
  
  # Add tags for better resource management
  labels = merge(
    local.common_tags,
    {
      Component = "storage"
      ManagedBy = "terraform"
    }
  )
}

# Create service account for the application
resource "google_service_account" "app" {
  account_id   = "${var.environment}-app-sa"
  display_name = "${var.environment} Application Service Account"
  project      = var.project_id
}

# Grant IAM roles to the service account
resource "google_project_iam_member" "app_sa_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Create Cloud Run service with production-grade configuration
module "cloud_run" {
  source = "../modules/cloud_run"

  project_id   = var.project_id
  region       = var.region
  service_name = "${var.environment}-photo-portfolio"
  
  # Container image configuration
  image = "gcr.io/${var.project_id}/photo-portfolio:${var.image_tag}"
  
  # Service account and identity
  service_account_email = google_service_account.app.email
  
  # Database connection
  cloudsql_connection_name = module.cloud_sql.connection_name
  
  # Environment variables
  environment_variables = {
    # Application settings
    ENVIRONMENT          = var.environment
    NODE_ENV             = "production"
    
    # Database configuration
    DB_HOST              = "/cloudsql/${module.cloud_sql.connection_name}"
    DB_NAME              = var.database_name
    DB_USER              = var.database_user
    DB_PORT              = "5432"
    
    # Storage configuration
    GCS_BUCKET           = module.cloud_storage.bucket_name
    
    # Application settings
    DEBUG                = "false"
    LOG_LEVEL            = "info"
    
    # Security
    SECURE_COOKIE        = "true"
    TRUST_PROXY          = "true"
    
    # CORS
    CORS_ORIGIN          = "https://${var.domain_name}"
    
    # Google Cloud Project
    GOOGLE_CLOUD_PROJECT = var.project_id
  }
  
  # Secret environment variables (referencing Secret Manager)
  secret_environment_variables = {
    "DATABASE_PASSWORD" = {
      secret_name = google_secret_manager_secret.db_password.secret_id
      secret_key  = "latest"
    },
    "SECRET_KEY" = {
      secret_name = google_secret_manager_secret.secret_key.secret_id
      secret_key  = "latest"
    },
    "JWT_SECRET_KEY" = {
      secret_name = google_secret_manager_secret.jwt_secret_key.secret_id
      secret_key  = "latest"
    },
    "GCS_CREDENTIALS" = {
      secret_name = "${var.environment}-gcs-credentials"
      secret_key  = "credentials.json"
    }
  }
  
  # Resource configuration
  container_concurrency = 80  # Max concurrent requests per container
  timeout_seconds      = 300  # 5 minutes
  
  # Resource limits
  cpu    = "2000m"  # 2 vCPUs
  memory = "2Gi"    # 2GB RAM
  
  # Auto-scaling
  min_instances = 1
  max_instances = 10
  
  # VPC Connector for private connectivity
  vpc_connector = module.vpc.vpc_connector_name
  
  # Security
  allow_public_access = false  # Require IAM authentication
  
  # Domain mapping
  domain_name = var.domain_name != "" ? var.domain_name : null
  
  # Traffic splitting (for blue-green deployments)
  traffic_split = [
    {
      revision_name = "${var.environment}-photo-portfolio-00001"
      percent       = 100
    }
  ]
  
  # Liveness and readiness probes
  liveness_probe = {
    path = "/health"
    initial_delay_seconds = 10
    timeout_seconds = 5
    period_seconds = 10
    failure_threshold = 3
  }
  
  readiness_probe = {
    path = "/ready"
    initial_delay_seconds = 5
    timeout_seconds = 5
    period_seconds = 10
    success_threshold = 1
    failure_threshold = 3
  }
  
  # Add labels for better resource management
  labels = merge(
    local.common_tags,
    {
      Component = "api"
      ManagedBy = "terraform"
    }
  )
}

# Create and manage secrets in Secret Manager
# This section creates and manages all application secrets with proper access controls

# Database password secret
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.environment}-db-password"
  
  replication {
    auto {}
  }
  
  # Add labels for better resource management
  labels = merge(
    local.common_tags,
    {
      Component = "secret"
      Type      = "database"
    }
  )
  
  # Enable automatic secret version destruction
  lifecycle {
    prevent_destroy = false
  }
  
  depends_on = [google_project_service.secretmanager_api]
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.database_password
  
  # Ensure secret is updated when the value changes
  lifecycle {
    create_before_destroy = true
  }
}

# Application secret key
resource "google_secret_manager_secret" "secret_key" {
  secret_id = "${var.environment}-secret-key"
  
  replication {
    auto {}
  }
  
  labels = merge(
    local.common_tags,
    {
      Component = "secret"
      Type      = "app"
    }
  )
}

resource "google_secret_manager_secret_version" "secret_key_version" {
  secret      = google_secret_manager_secret.secret_key.id
  secret_data = var.secret_key
  
  lifecycle {
    create_before_destroy = true
  }
}

# JWT secret key
resource "google_secret_manager_secret" "jwt_secret_key" {
  secret_id = "${var.environment}-jwt-secret-key"
  
  replication {
    auto {}
  }
  
  labels = merge(
    local.common_tags,
    {
      Component = "secret"
      Type      = "auth"
    }
  )
}

resource "google_secret_manager_secret_version" "jwt_secret_key_version" {
  secret      = google_secret_manager_secret.jwt_secret_key.id
  secret_data = var.jwt_secret_key
  
  lifecycle {
    create_before_destroy = true
  }
}

# GCS Service Account Key (for direct GCS operations if needed)
resource "google_secret_manager_secret" "gcs_credentials" {
  secret_id = "${var.environment}-gcs-credentials"
  
  replication {
    auto {}
  }
  
  labels = merge(
    local.common_tags,
    {
      Component = "secret"
      Type      = "storage"
    }
  )
}

# Grant the Cloud Run service account access to the secrets
resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each = toset([
    google_secret_manager_secret.db_password.secret_id,
    google_secret_manager_secret.secret_key.secret_id,
    google_secret_manager_secret.jwt_secret_key.secret_id,
    google_secret_manager_secret.gcs_credentials.secret_id
  ])
  
  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
  
  # Ensure IAM bindings are updated after secrets are created
  depends_on = [
    google_secret_manager_secret.db_password,
    google_secret_manager_secret.secret_key,
    google_secret_manager_secret.jwt_secret_key,
    google_secret_manager_secret.gcs_credentials
  ]
}

# Enable required Google Cloud APIs
# This section enables all necessary APIs for the application

# Map of APIs to enable with their display names
locals {
  required_apis = [
    # Core services
    "cloudresourcemanager.googleapis.com",  # Cloud Resource Manager API
    "serviceusage.googleapis.com",         # Service Usage API
    
    # Compute and Networking
    "compute.googleapis.com",              # Compute Engine API
    "vpcaccess.googleapis.com",           # Serverless VPC Access API
    "servicenetworking.googleapis.com",    # Service Networking API
    "dns.googleapis.com",                 # Cloud DNS API
    "cloudkms.googleapis.com",            # Cloud Key Management Service (KMS) API
    
    # Container and Serverless
    "run.googleapis.com",                 # Cloud Run Admin API
    "cloudbuild.googleapis.com",          # Cloud Build API
    "containerregistry.googleapis.com",   # Container Registry API
    "artifactregistry.googleapis.com",    # Artifact Registry API
    "cloudscheduler.googleapis.com",      # Cloud Scheduler API
    "workflows.googleapis.com",           # Workflows API
    "eventarc.googleapis.com",            # Eventarc API
    "cloudfunctions.googleapis.com",      # Cloud Functions API
    
    # Database
    "sqladmin.googleapis.com",            # Cloud SQL Admin API
    "spanner.googleapis.com",             # Cloud Spanner API (if needed)
    "firestore.googleapis.com",          # Cloud Firestore API
    "firebaserules.googleapis.com",       # Firebase Rules API
    
    # Storage
    "storage-api.googleapis.com",         # Google Cloud Storage JSON API
    "storage-component.googleapis.com",   # Google Cloud Storage
    "storage.googleapis.com",             # Cloud Storage API
    
    # Security and Identity
    "secretmanager.googleapis.com",       # Secret Manager API
    "iam.googleapis.com",                 # Identity and Access Management (IAM) API
    "iamcredentials.googleapis.com",      # IAM Service Account Credentials API
    "cloudkms.googleapis.com",           # Cloud Key Management Service (KMS) API
    "cloudasset.googleapis.com",          # Cloud Asset API
    "cloudscheduler.googleapis.com",      # Cloud Scheduler API
    
    # Monitoring and Logging
    "monitoring.googleapis.com",          # Cloud Monitoring API
    "logging.googleapis.com",             # Cloud Logging API
    "cloudtrace.googleapis.com",          # Cloud Trace API
    "errorreporting.googleapis.com",      # Error Reporting API
    "cloudprofiler.googleapis.com",       # Cloud Profiler API
    "clouddebugger.googleapis.com",       # Cloud Debugger API
    "cloudtrace.googleapis.com",          # Cloud Trace API
    
    # Additional services
    "appengine.googleapis.com",           # App Engine Admin API
    "cloudtasks.googleapis.com",          # Cloud Tasks API
    "cloudbilling.googleapis.com",        # Cloud Billing API
    "cloudbillingbudgets.googleapis.com", # Cloud Billing Budget API
  ]
}

# Enable all required APIs
resource "google_project_service" "required_apis" {
  for_each = toset(local.required_apis)
  
  service = each.value
  
  # Don't disable the API on destroy to prevent accidental service disruption
  disable_on_destroy = false
  
  # Add a delay after API enablement to avoid rate limiting
  provisioner "local-exec" {
    command = "sleep 15"
  }
  
  # Ensure the project is created before enabling APIs
  depends_on = [
    google_project_service.required_apis["cloudresourcemanager.googleapis.com"]
  ]
}

# Create a service account for the application
resource "google_service_account" "app" {
  account_id   = "${var.environment}-app-sa"
  display_name = "${title(var.environment)} Application Service Account"
  description  = "Service account for the ${var.environment} environment of the Photo Portfolio application"
  
  # Ensure the service account is created after the IAM API is enabled
  depends_on = [
    google_project_service.required_apis["iam.googleapis.com"]
  ]
}

# Grant IAM roles to the service account
resource "google_project_iam_member" "app_sa_roles" {
  for_each = toset([
    # Cloud Run
    "roles/run.invoker",
    "roles/run.developer",
    
    # Cloud SQL
    "roles/cloudsql.client",
    
    # Cloud Storage
    "roles/storage.objectAdmin",
    "roles/storage.objectViewer",
    
    # Logging and Monitoring
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent",
    "roles/errorreporting.writer",
    "roles/cloudprofiler.agent",
    "roles/clouddebugger.agent",
    
    # Secret Manager
    "roles/secretmanager.secretAccessor",
    
    # Service Account User (required for Cloud Run to use the service account)
    "roles/iam.serviceAccountUser"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app.email}"
  
  # Ensure the IAM API is enabled before applying IAM policies
  depends_on = [
    google_project_service.required_apis["iam.googleapis.com"],
    google_service_account.app
  ]
}

# Outputs
# This section defines all output values that will be displayed after Terraform applies

# Application URLs
output "application_url" {
  description = "The base URL of the deployed application"
  value       = "https://${var.domain_name != "" ? var.domain_name : module.cloud_run.service_url}"
}

output "api_documentation_url" {
  description = "The URL to the API documentation (Swagger/OpenAPI)"
  value       = "${var.domain_name != "" ? "https://${var.domain_name}" : module.cloud_run.service_url}/api-docs"
}

# Cloud Run Outputs
output "cloud_run_service_url" {
  description = "The URL of the Cloud Run service"
  value       = module.cloud_run.service_url
}

output "cloud_run_service_name" {
  description = "The name of the Cloud Run service"
  value       = module.cloud_run.service_name
}

# Cloud SQL Outputs
output "cloud_sql_connection_name" {
  description = "The connection name of the Cloud SQL instance"
  value       = module.cloud_sql.connection_name
}

output "cloud_sql_instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = module.cloud_sql.instance_name
}

output "cloud_sql_private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = module.cloud_sql.private_ip_address
}

# Cloud Storage Outputs
output "cloud_storage_bucket_name" {
  description = "The name of the Cloud Storage bucket"
  value       = module.cloud_storage.bucket_name
}

output "cloud_storage_url" {
  description = "The base URL of the Cloud Storage bucket"
  value       = "https://storage.cloud.google.com/${module.cloud_storage.bucket_name}"
}

# Service Account Outputs
output "service_account_email" {
  description = "The email of the service account used by the application"
  value       = google_service_account.app.email
}

output "service_account_name" {
  description = "The name of the service account"
  value       = google_service_account.app.name
}

# VPC Outputs
output "vpc_name" {
  description = "The name of the VPC network"
  value       = module.vpc.vpc_name
}

output "vpc_connector_name" {
  description = "The name of the VPC connector"
  value       = module.vpc.vpc_connector_name
}

# Secret Manager Outputs
output "secret_names" {
  description = "Map of secret names created in Secret Manager"
  value = {
    db_password    = google_secret_manager_secret.db_password.secret_id
    secret_key      = google_secret_manager_secret.secret_key.secret_id
    jwt_secret_key  = google_secret_manager_secret.jwt_secret_key.secret_id
    gcs_credentials = google_secret_manager_secret.gcs_credentials.secret_id
  }
  sensitive = true
}

# Monitoring and Logging
output "cloud_run_logs_url" {
  description = "The URL to view logs for the Cloud Run service"
  value       = "https://console.cloud.google.com/run/detail/${var.region}/${module.cloud_run.service_name}/logs?project=${var.project_id}"
}

output "cloud_sql_metrics_url" {
  description = "The URL to view metrics for the Cloud SQL instance"
  value       = "https://console.cloud.google.com/sql/instances/${module.cloud_sql.instance_name}/monitoring?project=${var.project_id}"
}

# Environment Information
output "environment_info" {
  description = "Information about the deployed environment"
  value = {
    environment = var.environment
    project_id  = var.project_id
    region      = var.region
    zone        = var.zone
    deployed_at = timestamp()
  }
}

# Instructions for next steps
output "next_steps" {
  description = "Instructions for next steps after deployment"
  value = <<EOT

  Deployment completed successfully! Here are the next steps:

  1. Access your application: ${var.domain_name != "" ? "https://${var.domain_name}" : module.cloud_run.service_url}
  2. View API documentation: ${var.domain_name != "" ? "https://${var.domain_name}/api-docs" : "${module.cloud_run.service_url}/api-docs"}
  3. Monitor your application: https://console.cloud.google.com/run?project=${var.project_id}
  4. View logs: ${self.cloud_run_logs_url}

  To make changes to your infrastructure, update the Terraform configuration and run:
    terraform plan
    terraform apply

  EOT
}
