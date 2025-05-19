output "cloud_run_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = module.cloud_run.service_url
}

output "cloud_sql_connection_name" {
  description = "The connection name of the Cloud SQL instance"
  value       = module.cloud_sql.connection_name
}

output "cloud_sql_private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = module.cloud_sql.private_ip
}

output "cloud_storage_bucket" {
  description = "The name of the Cloud Storage bucket"
  value       = module.cloud_storage.bucket_name
}

output "service_account_email" {
  description = "The email of the service account used by the application"
  value       = google_service_account.app.email
}

output "database_name" {
  description = "The name of the database"
  value       = var.database_name
}

output "database_user" {
  description = "The database user name"
  value       = var.database_user
  sensitive   = true
}

output "vpc_name" {
  description = "The name of the VPC"
  value       = module.vpc.vpc_name
}

output "subnet_name" {
  description = "The name of the subnet"
  value       = module.vpc.subnet_name
}

output "vpc_connector_name" {
  description = "The name of the VPC connector"
  value       = module.vpc.vpc_connector_name
}
