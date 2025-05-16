# Cloud Run Outputs
output "cloud_run_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = module.cloud_run.service_url
}

output "cloud_run_service_name" {
  description = "The name of the Cloud Run service"
  value       = module.cloud_run.service_name
}

output "cloud_run_location" {
  description = "The location (region) where Cloud Run is deployed"
  value       = module.cloud_run.location
}

# Cloud SQL Outputs
output "cloud_sql_connection_name" {
  description = "The connection name of the Cloud SQL instance for use with Cloud Run"
  value       = module.cloud_sql.connection_name
}

output "cloud_sql_instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = module.cloud_sql.instance_name
}

output "cloud_sql_private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = module.cloud_sql.private_ip
}

output "cloud_sql_public_ip" {
  description = "The public IP address of the Cloud SQL instance"
  value       = module.cloud_sql.public_ip_address
  sensitive   = true
}

# Cloud Storage Outputs
output "cloud_storage_bucket" {
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

# Database Outputs
output "database_name" {
  description = "The name of the database"
  value       = var.database_name
  sensitive   = true
}

output "database_user" {
  description = "The database user name"
  value       = var.database_user
  sensitive   = true
}

# VPC Outputs
output "vpc_name" {
  description = "The name of the VPC network"
  value       = module.vpc.vpc_name
}

output "vpc_self_link" {
  description = "The self-link of the VPC network"
  value       = module.vpc.vpc_self_link
}

output "subnet_name" {
  description = "The name of the subnet"
  value       = module.vpc.subnet_name
}

output "subnet_self_link" {
  description = "The self-link of the subnet"
  value       = module.vpc.subnet_self_link
}

output "vpc_connector_name" {
  description = "The name of the VPC connector for Serverless VPC Access"
  value       = module.vpc.vpc_connector_name
}

# Secret Manager Outputs
output "secret_names" {
  description = "Map of secret names created in Secret Manager"
  value = {
    db_password    = google_secret_manager_secret.db_password.secret_id
    secret_key      = google_secret_manager_secret.secret_key.secret_id
    jwt_secret_key  = google_secret_manager_secret.jwt_secret_key.secret_id
  }
  sensitive = true
}

# API Endpoints
output "api_endpoints" {
  description = "Map of API endpoints"
  value = {
    api_base_url = module.cloud_run.service_url
    health_check = "${module.cloud_run.service_url}/health"
    api_docs     = "${module.cloud_run.service_url}/docs"
  }
}

# Current Configuration
output "current_configuration" {
  description = "Current configuration values"
  value = {
    project_id   = var.project_id
    environment  = var.environment
    region       = var.region
    zone         = var.zone
  }
}
