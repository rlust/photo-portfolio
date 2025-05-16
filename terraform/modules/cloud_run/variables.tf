variable "project_id" {
  description = "The project ID to deploy to"
  type        = string
}

variable "region" {
  description = "The region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
}

variable "image" {
  description = "The container image to deploy"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables to set in the container"
  type        = map(string)
  default     = {}
}

variable "secret_environment_variables" {
  description = "Environment variables that reference secrets"
  type = map(object({
    secret_name = string
    secret_key  = string
  }))
  default = {}
}

variable "service_account_email" {
  description = "The email of the service account to run the service as"
  type        = string
}

variable "cloudsql_connection_name" {
  description = "The connection name of the Cloud SQL instance"
  type        = string
}

variable "allow_public_access" {
  description = "Whether to allow unauthenticated access to the service"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Custom domain name to map to the service"
  type        = string
  default     = ""
}

variable "cpu" {
  description = "CPU allocation"
  type        = string
  default     = "1000m"
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "512Mi"
}

variable "container_concurrency" {
  description = "Maximum number of concurrent requests each container can handle"
  type        = number
  default     = 80
}

variable "timeout_seconds" {
  description = "Maximum request timeout in seconds"
  type        = number
  default     = 300
}

variable "annotations" {
  description = "Additional annotations for the Cloud Run service"
  type        = map(string)
  default     = {}
}
