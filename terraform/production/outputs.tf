# Generated Secrets (for reference, handle with care)
output "database_password" {
  description = "The generated database password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "secret_key" {
  description = "The generated application secret key"
  value       = random_password.secret_key.result
  sensitive   = true
}

output "jwt_secret" {
  description = "The generated JWT secret key"
  value       = random_password.jwt_secret.result
  sensitive   = true
}

# Cloud Run Service Outputs
output "cloud_run_service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = try(google_cloud_run_service.service.status[0].url, "")
}

output "cloud_run_service_name" {
  description = "The name of the Cloud Run service"
  value       = try(google_cloud_run_service.service.name, "")
}

# Cloud SQL Outputs
output "cloud_sql_instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = try(google_sql_database_instance.main.name, "")
}

output "cloud_sql_connection_name" {
  description = "The connection name of the Cloud SQL instance"
  value       = try(google_sql_database_instance.main.connection_name, "")
}

output "cloud_sql_public_ip_address" {
  description = "The public IPv4 address of the Cloud SQL instance"
  value       = try(google_sql_database_instance.main.public_ip_address, "")
  sensitive   = true
}

output "cloud_sql_private_ip_address" {
  description = "The private IPv4 address of the Cloud SQL instance"
  value       = try(google_sql_database_instance.main.private_ip_address, "")
  sensitive   = true
}

# Cloud Storage Outputs
output "cloud_storage_bucket_name" {
  description = "The name of the Cloud Storage bucket"
  value       = try(google_storage_bucket.bucket.name, "")
}

output "cloud_storage_bucket_self_link" {
  description = "The self-link of the Cloud Storage bucket"
  value       = try(google_storage_bucket.bucket.self_link, "")
}

# Service Account Outputs
output "service_account_email" {
  description = "The email of the service account created for the application"
  value       = try(google_service_account.app.email, "")
}

output "service_account_name" {
  description = "The fully-qualified name of the service account"
  value       = try(google_service_account.app.name, "")
}

# VPC Outputs
output "vpc_name" {
  description = "The name of the VPC network"
  value       = try(google_compute_network.vpc.name, "")
}

output "vpc_self_link" {
  description = "The self-link of the VPC network"
  value       = try(google_compute_network.vpc.self_link, "")
}

output "subnet_name" {
  description = "The name of the subnet"
  value       = try(google_compute_subnetwork.subnet.name, "")
}

output "subnet_self_link" {
  description = "The self-link of the subnet"
  value       = try(google_compute_subnetwork.subnet.self_link, "")
}

# Database Outputs
output "database_name" {
  description = "The name of the database"
  value       = try(google_sql_database.database.name, "")
}

output "database_self_link" {
  description = "The self-link of the database"
  value       = try(google_sql_database.database.self_link, "")
}

# Secret Manager Outputs (commented out as they require additional setup)
# output "db_password_secret_name" {
#   description = "The name of the database password secret"
#   value       = try(google_secret_manager_secret.db_password.name, "")
# }
# 
# output "secret_key_secret_name" {
#   description = "The name of the application secret key"
#   value       = try(google_secret_manager_secret.secret_key.name, "")
# }
# 
# output "jwt_secret_key_secret_name" {
#   description = "The name of the JWT secret key"
#   value       = try(google_secret_manager_secret.jwt_secret_key.name, "")
# }

# Additional Useful Outputs
output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "environment" {
  description = "The environment name"
  value       = var.environment
}
