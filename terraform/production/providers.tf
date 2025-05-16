terraform {
  required_version = ">= 1.3.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.51"
      
      configuration_aliases = [
        google.impersonation
      ]
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.51"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.14"
    }
  }
}

# Default provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
  
  # Add any additional provider configurations here
  # such as impersonation or custom endpoints
}

# Beta provider for features not yet in GA
provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Provider for impersonation (if using service account impersonation)
provider "google" {
  alias   = "impersonation"
  project = var.project_id
  region  = var.region
  
  # Uncomment and configure if using service account impersonation
  # impersonate_service_account = "terraform@${var.project_id}.iam.gserviceaccount.com"
}
