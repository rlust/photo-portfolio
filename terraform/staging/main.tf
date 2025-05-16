provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Create a random ID for unique resource naming
resource "random_id" "suffix" {
  byte_length = 4
}

# Create VPC
module "vpc" {
  source = "../modules/vpc"

  project_id = var.project_id
  vpc_name   = "${var.environment}-vpc"
  region     = var.region
  subnet_cidr = var.subnet_cidr
  
  # Only allow SSH from specific IPs in staging
  allowed_ssh_ips = var.allowed_ssh_ips
}

# Create Cloud SQL instance
module "cloud_sql" {
  source = "../modules/cloud_sql"

  project_id        = var.project_id
  region            = var.region
  zone              = var.zone
  instance_name     = "${var.environment}-sql-${random_id.suffix.hex}"
  database_name     = var.database_name
  user_name         = var.database_user
  user_password     = var.database_password
  tier              = var.database_tier
  availability_type = var.database_availability_type
  disk_size         = var.database_disk_size
  vpc_network       = module.vpc.vpc_self_link
}

# Create Cloud Storage bucket
module "cloud_storage" {
  source = "../modules/cloud_storage"

  project_id  = var.project_id
  bucket_name = "${var.project_id}-${var.environment}-${random_id.suffix.hex}"
  location    = var.region
  
  versioning_enabled = true
  force_destroy      = true  # For staging, allow bucket destruction
  
  service_account_email = google_service_account.app.email
  
  lifecycle_rules = [
    {
      action = {
        type          = "Delete"
        storage_class = ""
      }
      condition = {
        age                   = 30  # Delete objects older than 30 days
        created_before        = ""
        with_state            = "ANY"
        matches_storage_class = ["STANDARD"]
        num_newer_versions    = 0
      }
    }
  ]
  
  cors = {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
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

# Create Cloud Run service
module "cloud_run" {
  source = "../modules/cloud_run"

  project_id  = var.project_id
  region      = var.region
  service_name = "${var.environment}-photo-portfolio"
  
  # Image will be set during deployment
  image = "gcr.io/${var.project_id}/photo-portfolio:${var.image_tag}"
  
  service_account_email = google_service_account.app.email
  cloudsql_connection_name = module.cloud_sql.connection_name
  
  # Environment variables
  environment_variables = {
    ENVIRONMENT          = var.environment
    DATABASE_URL         = "postgresql://${var.database_user}:${var.database_password}@//cloudsql/${module.cloud_sql.connection_name}/${var.database_name}"
    GCS_BUCKET           = module.cloud_storage.bucket_name
    SECRET_KEY           = var.secret_key
    JWT_SECRET_KEY       = var.jwt_secret_key
    GOOGLE_CLOUD_PROJECT = var.project_id
  }
  
  # Secret environment variables
  secret_environment_variables = {
    "DATABASE_PASSWORD" = {
      secret_name = "${var.environment}-db-password"
      secret_key  = "latest"
    }
    "SECRET_KEY" = {
      secret_name = "${var.environment}-secret-key"
      secret_key  = "latest"
    }
    "JWT_SECRET_KEY" = {
      secret_name = "${var.environment}-jwt-secret-key"
      secret_key  = "latest"
    }
  }
  
  # Resource limits
  cpu    = var.cpu
  memory = var.memory
  
  # Allow public access
  allow_public_access = true
  
  # Custom domain (optional)
  domain_name = var.domain_name != "" ? "${var.environment}.${var.domain_name}" : ""
}

# Create secrets
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.environment}-db-password"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.secretmanager_api]
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret = google_secret_manager_secret.db_password.id
  secret_data = var.database_password
}

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "${var.environment}-secret-key"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "secret_key_version" {
  secret = google_secret_manager_secret.secret_key.id
  secret_data = var.secret_key
}

resource "google_secret_manager_secret" "jwt_secret_key" {
  secret_id = "${var.environment}-jwt-secret-key"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_secret_key_version" {
  secret = google_secret_manager_secret.jwt_secret_key.id
  secret_data = var.jwt_secret_key
}

# Grant the service account access to the secrets
resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each = toset([
    google_secret_manager_secret.db_password.secret_id,
    google_secret_manager_secret.secret_key.secret_id,
    google_secret_manager_secret.jwt_secret_key.secret_id
  ])
  
  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "containerregistry.googleapis.com"
  ])
  
  service = each.value
  disable_on_destroy = false
}

# Outputs
output "cloud_run_url" {
  value = module.cloud_run.service_url
}

output "cloud_sql_connection_name" {
  value = module.cloud_sql.connection_name
}

output "cloud_storage_bucket" {
  value = module.cloud_storage.bucket_name
}

output "service_account_email" {
  value = google_service_account.app.email
}
