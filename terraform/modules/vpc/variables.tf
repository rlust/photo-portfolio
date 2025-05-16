variable "project_id" {
  description = "The project ID to deploy to"
  type        = string
}

variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
  default     = "photo-portfolio-vpc"
}

variable "region" {
  description = "The region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "subnet_cidr" {
  description = "The CIDR range for the subnet"
  type        = string
  default     = "10.10.0.0/20"
}

variable "flow_logs" {
  description = "Enable VPC flow logs"
  type        = bool
  default     = true
}

variable "allowed_ssh_ips" {
  description = "List of IP addresses allowed to SSH to instances"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "vpc_connector_cidr" {
  description = "The CIDR range for the VPC connector"
  type        = string
  default     = "10.8.0.0/28"
}
