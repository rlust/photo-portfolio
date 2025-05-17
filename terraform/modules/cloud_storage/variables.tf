variable "project_id" {
  description = "The ID of the project to create the bucket in"
  type        = string
}

variable "bucket_name" {
  description = "The name of the bucket"
  type        = string
}

variable "location" {
  description = "The location of the bucket"
  type        = string
  default     = "US"
}

variable "storage_class" {
  description = "The storage class of the bucket"
  type        = string
  default     = "STANDARD"
}

variable "versioning_enabled" {
  description = "Enable versioning for the bucket"
  type        = bool
  default     = true
}

variable "force_destroy" {
  description = "When deleting the bucket, delete all objects in the bucket"
  type        = bool
  default     = false
}

variable "cors" {
  description = "CORS configuration for the bucket"
  type = object({
    origin          = list(string)
    method          = list(string)
    response_header = list(string)
    max_age_seconds = number
  })
  default = null
}

variable "lifecycle_rules" {
  description = "List of lifecycle rules"
  type = list(object({
    action = object({
      type          = string
      storage_class = string
    })
    condition = object({
      age                   = number
      created_before        = string
      with_state            = string
      matches_storage_class = list(string)
      num_newer_versions    = number
    })
  }))
  default = []
}

variable "iam_members" {
  description = "Map of IAM members with their roles"
  type = map(object({
    role   = string
    member = string
  }))
  default = {}
}

variable "default_acl" {
  description = "Default object ACL"
  type        = list(string)
  default     = null
}

variable "prevent_public_access" {
  description = "Prevent public access to the bucket"
  type        = bool
  default     = true
}

variable "service_account_email" {
  description = "Email of the service account to grant permissions to"
  type        = string
}

variable "additional_viewers" {
  description = "List of additional members with viewer access"
  type        = list(string)
  default     = []
}
