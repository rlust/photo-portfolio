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



variable "subnet_cidr" {
  description = "The CIDR range for the subnet"
  type        = string
  default     = "10.10.0.0/20"
}

variable "allowed_ssh_ips" {
  description = "List of IP addresses allowed to SSH to instances"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "database_name" {
  description = "The name of the database"
  type        = string
  default     = "photoportfolio"
}

variable "database_user" {
  description = "The database user name"
  type        = string
  default     = "rlust"
}

variable "database_password" {
  description = "The database user password"
  type        = string
  sensitive   = true
}

variable "database_tier" {
  description = "The database instance tier"
  type        = string
  default     = "db-g1-small"  # More powerful instance for production
}

variable "database_availability_type" {
  description = "The availability type of the database instance"
  type        = string
  default     = "REGIONAL"  # High availability for production
}

variable "database_disk_size" {
  description = "The disk size for the database in GB"
  type        = number
  default     = 50  # Larger disk size for production
}

variable "secret_key" {
  description = "The secret key for the application"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "The secret key for JWT token generation"
  type        = string
  sensitive   = true
}

variable "cpu" {
  description = "The number of CPUs to allocate to the Cloud Run service"
  type        = string
  default     = "2000m"  # More CPU for production
}

variable "memory" {
  description = "The amount of memory to allocate to the Cloud Run service"
  type        = string
  default     = "2Gi"  # More memory for production
}

# Network
variable "domain_name" {
  description = "The custom domain name for the application (required for production)"
  type        = string
  default     = ""  # Required in production - must be set in terraform.tfvars
  validation {
    condition     = var.domain_name != ""
    error_message = "Domain name is required for production environment."
  }
}

variable "subnet_cidr" {
  description = "The CIDR range for the subnet"
  type        = string
  default     = "10.10.0.0/20"
}

variable "allowed_ssh_ips" {
  description = "List of IP addresses allowed to SSH to instances"
  type        = list(string)
  default     = []
}

variable "create_vpc" {
  description = "Whether to create a new VPC"
  type        = bool
  default     = true
}

variable "vpc_name" {
  description = "Name of the existing VPC to use"
  type        = string
  default     = ""
}

variable "subnet_name" {
  description = "Name of the existing subnet to use"
  type        = string
  default     = ""
}

# Database
variable "database_name" {
  description = "The name of the database"
  type        = string
  default     = "photoportfolio"
}

variable "database_user" {
  description = "The database user name"
  type        = string
  default     = "rlust"
}

variable "database_password" {
  description = "The database user password"
  type        = string
  sensitive   = true
}

variable "database_tier" {
  description = "The database instance tier"
  type        = string
  default     = "db-g1-small"
}

variable "database_availability_type" {
  description = "The availability type of the database instance"
  type        = string
  default     = "REGIONAL"
}

variable "database_disk_size" {
  description = "The disk size for the database in GB"
  type        = number
  default     = 50
}

variable "database_instance_name" {
  description = "Name of the existing database instance to use"
  type        = string
  default     = ""
}

variable "create_database" {
  description = "Whether to create a new database instance"
  type        = bool
  default     = true
}

# Cloud Storage
variable "create_storage_bucket" {
  description = "Whether to create a new storage bucket"
  type        = bool
  default     = true
}

variable "existing_bucket_name" {
  description = "Name of the existing storage bucket to use"
  type        = string
  default     = ""
}

# Service Account
variable "create_service_account" {
  description = "Whether to create a new service account"
  type        = bool
  default     = true
}

variable "service_account_email" {
  description = "Email of the existing service account to use"
  type        = string
  default     = ""
}

# Cloud Run
variable "image_tag" {
  description = "The Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 5
}

variable "cpu" {
  description = "The number of CPUs to allocate to the Cloud Run service"
  type        = string
  default     = "2000m"
}

variable "memory" {
  description = "The amount of memory to allocate to the Cloud Run service"
  type        = string
  default     = "2Gi"
}

# Secrets
variable "secret_key" {
  description = "The secret key for the application"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "The secret key for JWT token generation"
  type        = string
  sensitive   = true
}

# Monitoring
variable "enable_monitoring" {
  description = "Whether to enable monitoring resources"
  type        = bool
  default     = true
}

# Logging
variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

# Feature Flags
variable "enable_cdn" {
  description = "Whether to enable Cloud CDN"
  type        = bool
  default     = true
}

variable "enable_ssl" {
  description = "Whether to enable SSL for the load balancer"
  type        = bool
  default     = true
}

# Cost Management
variable "budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 100
}

variable "budget_alert_spend_basis" {
  description = "The type of basis used to determine if spend has passed the threshold"
  type        = string
  default     = "CURRENT_SPEND"
}

variable "budget_alert_spend_percent" {
  description = "Percent of the budget to alert on"
  type        = number
  default     = 0.5
}

# Notifications
variable "notification_email_addresses" {
  description = "List of email addresses to send budget notifications to"
  type        = list(string)
  default     = []
}

variable "image_tag" {
  description = "The Docker image tag to deploy"
  type        = string
  default     = "latest"
}
