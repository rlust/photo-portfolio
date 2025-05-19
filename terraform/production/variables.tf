
# Project and Environment
variable "project_id" {
  description = "The GCP project ID"
  type        = string
  validation {
    condition     = length(var.project_id) > 0
    error_message = "Project ID is required"
  }
}

variable "project_number" {
  description = "The GCP project number"
  type        = string
  default     = ""
}

variable "environment" {
  description = "The environment name (e.g., staging, production)"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'"
  }
}

# Region and Zone
variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
  
  validation {
    condition     = contains(["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"], var.region)
    error_message = "Unsupported region. Supported regions: us-central1, us-east1, us-west1, europe-west1, asia-east1"
  }
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
  
  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+-[a-z]$", var.zone))
    error_message = "Zone must be in the format 'region-zone' (e.g., 'us-central1-a')"
  }
}

# Domain
variable "domain_name" {
  description = "The domain name for the application (e.g., example.com)"
  type        = string
  default     = ""
}

# Service Account
variable "service_account_email" {
  description = "Email of the existing service account to use"
  type        = string
  default     = ""
}

# Database
variable "database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "photo_portfolio"
}

variable "database_user" {
  description = "Name of the database user"
  type        = string
  default     = "app_user"
}

variable "database_password" {
  description = "Password for the database user"
  type        = string
  sensitive   = true
}

variable "database_tier" {
  description = "The machine type to use for the database"
  type        = string
  default     = "db-f1-micro"
}

variable "database_availability_type" {
  description = "The availability type of the Cloud SQL instance"
  type        = string
  default     = "ZONAL"
  
  validation {
    condition     = contains(["REGIONAL", "ZONAL"], var.database_availability_type)
    error_message = "Availability type must be either 'REGIONAL' or 'ZONAL'"
  }
}

variable "database_disk_size" {
  description = "The size of the disk in GB"
  type        = number
  default     = 10
}

# Application
variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "cpu" {
  description = "Number of CPU units for Cloud Run service"
  type        = string
  default     = "1000m"
}

variable "memory" {
  description = "Amount of memory for Cloud Run service"
  type        = string
  default     = "512Mi"
}

# Secrets
variable "secret_key" {
  description = "Secret key for the application"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "Secret key for JWT token generation"
  type        = string
  sensitive   = true
}
