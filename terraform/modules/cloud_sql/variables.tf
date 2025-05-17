variable "project_id" {
  description = "The project ID to deploy to"
  type        = string
}

variable "region" {
  description = "The region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The zone to deploy to"
  type        = string
  default     = "us-central1-a"
}

variable "instance_name" {
  description = "The name of the Cloud SQL instance"
  type        = string
}

variable "database_version" {
  description = "The database version to use"
  type        = string
  default     = "POSTGRES_14"
}

variable "tier" {
  description = "The machine type to use"
  type        = string
  default     = "db-f1-micro"
}

variable "availability_type" {
  description = "The availability type of the Cloud SQL instance"
  type        = string
  default     = "ZONAL"
}

variable "disk_size" {
  description = "The size of the disk in GB"
  type        = number
  default     = 10
}

variable "disk_type" {
  description = "The type of the disk"
  type        = string
  default     = "PD_SSD"
}

variable "backup_location" {
  description = "The location of the backup"
  type        = string
  default     = "us"
}

variable "retained_backups" {
  description = "Number of backups to retain"
  type        = number
  default     = 7
}

variable "vpc_network" {
  description = "The VPC network to use"
  type        = string
  default     = "default"
}

variable "database_name" {
  description = "The name of the database to create"
  type        = string
  default     = "photoportfolio"
}

variable "user_name" {
  description = "The name of the database user"
  type        = string
  default     = "rlust"
}

variable "user_password" {
  description = "The password for the database user"
  type        = string
  sensitive   = true
}

variable "deletion_protection" {
  description = "Whether to enable deletion protection"
  type        = bool
  default     = true
}
