# Get the current GCP project
data "google_project" "project" {}

# Get the current GCP client config for the provider
data "google_client_config" "current" {}

# Get the Cloud Run service account
data "google_service_account" "cloud_run" {
  account_id = "${var.project_number}-compute@developer.gserviceaccount.com"
}

# Get the available zones in the region
data "google_compute_zones" "available" {
  region = var.region
  status = "UP"
}

# Get the latest container image from Google Container Registry
data "google_container_registry_image" "app" {
  name   = "photo-portfolio"
  region = var.region
}

# Get the Cloud SQL instance if it exists
data "google_sql_database_instance" "existing" {
  count = var.create_database ? 0 : 1
  name  = var.database_instance_name
}

# Get the existing service account if not creating a new one
data "google_service_account" "existing" {
  count      = var.create_service_account ? 0 : 1
  account_id = var.service_account_email
}

# Get the existing VPC if not creating a new one
data "google_compute_network" "existing" {
  count = var.create_vpc ? 0 : 1
  name  = var.vpc_name
}

# Get the existing subnet if not creating a new one
data "google_compute_subnetwork" "existing" {
  count  = var.create_vpc ? 0 : 1
  name   = var.subnet_name
  region = var.region
}
