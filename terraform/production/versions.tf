terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
  
  # Required for state locking
  backend "gcs" {
    # Configured in backend.tf or via -backend-config
  }
}

# Provider versions
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
  
  # Add any additional provider configurations here
}

# Beta provider for features not yet in GA
provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Random provider for generating random values
provider "random" {}

# Null provider for resource dependencies
provider "null" {}

# Kubernetes provider (if needed)
provider "kubernetes" {
  config_path = "~/.kube/config"
}

# Helm provider (if needed)
provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}
