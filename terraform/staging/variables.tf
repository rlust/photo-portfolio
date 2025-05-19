variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "The environment name (e.g., staging, production)"
  type        = string
  default     = "staging"
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
  default     = "db-f1-micro"
}

variable "database_availability_type" {
  description = "The availability type of the database instance"
  type        = string
  default     = "ZONAL"
}

variable "database_disk_size" {
  description = "The disk size for the database in GB"
  type        = number
  default     = 10
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
  default     = "1000m"
}

variable "memory" {
  description = "The amount of memory to allocate to the Cloud Run service"
  type        = string
  default     = "512Mi"
}

variable "domain_name" {
  description = "The custom domain name for the application"
  type        = string
  default     = ""
}

variable "image_tag" {
  description = "The Docker image tag to deploy"
  type        = string
  default     = "latest"
}
