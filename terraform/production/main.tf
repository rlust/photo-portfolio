# Generate random passwords for sensitive values
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "_%@"
  min_upper        = 1
  min_lower        = 1
  min_numeric      = 1
  min_special      = 1
}

resource "random_password" "secret_key" {
  length           = 32
  special          = true
  override_special = "_%@"
}

resource "random_password" "jwt_secret" {
  length           = 32
  special          = true
  override_special = "_%@"
}

locals {
  # Common tags to be assigned to all resources
  common_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = "photo-portfolio"
  }
  
  # Service name
  service_name = "photo-portfolio-${var.environment}"
}

# Enable required Google Cloud APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "containerregistry.googleapis.com",
    "servicenetworking.googleapis.com"
  ])
  
  service = each.value
  disable_on_destroy = false
}

# Create a service account for the application
resource "google_service_account" "app" {
  account_id   = "${var.environment}-app-sa"
  display_name = "${title(var.environment)} Application Service Account"
  description  = "Service account for the ${var.environment} environment of the Photo Portfolio application"
}

# Grant IAM roles to the service account
resource "google_project_iam_member" "app_sa_roles" {
  for_each = toset([
    "roles/run.invoker",
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    "roles/iam.serviceAccountUser"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app.email}"
  
  depends_on = [google_project_service.required_apis["iam.googleapis.com"]]
}

# Create a VPC network
resource "google_compute_network" "vpc" {
  name                    = "${var.environment}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  
  depends_on = [google_project_service.required_apis["compute.googleapis.com"]]
}

# Enable the Service Networking API
resource "google_project_service" "servicenetworking" {
  service = "servicenetworking.googleapis.com"
  disable_on_destroy = false
}

# Reserve an internal IP range for the private service connection
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "${var.environment}-private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  
  depends_on = [google_project_service.servicenetworking]
}

# Create a private service connection
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
  
  depends_on = [google_compute_global_address.private_ip_alloc]
}

# Create a subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.environment}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
  
  private_ip_google_access = true
}

# Create a Cloud SQL instance
resource "google_sql_database_instance" "main" {
  name             = "${var.environment}-sql"
  database_version = "POSTGRES_13"
  region           = var.region
  
  settings {
    tier              = var.database_tier
    availability_type = var.database_availability_type
    disk_size         = var.database_disk_size
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }
    
    backup_configuration {
      enabled    = true
      start_time = "02:00"
    }
    
    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }
  
  deletion_protection = false
  
  depends_on = [
    google_project_service.required_apis["sqladmin.googleapis.com"],
    google_service_networking_connection.private_vpc_connection
  ]
}

# Create a database
resource "google_sql_database" "database" {
  name     = var.database_name
  instance = google_sql_database_instance.main.name
}

# Create a database user
resource "google_sql_user" "user" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

# Create a Cloud Storage bucket
resource "google_storage_bucket" "bucket" {
  name          = "${var.project_id}-${var.environment}-storage"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
  
  depends_on = [google_project_service.required_apis["storage-api.googleapis.com"]]
}

# Create a Cloud Run service
resource "google_cloud_run_service" "service" {
  name     = local.service_name
  location = var.region
  
  lifecycle {
    ignore_changes = [
      template[0].spec[0].containers[0].image,
    ]
  }
  
  template {
    spec {
      containers {
        image = "gcr.io/photo-portfolio-459415/photo-portfolio-production:latest"
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${var.database_user}:${random_password.db_password.result}@//cloudsql/${google_sql_database_instance.main.connection_name}/${var.database_name}"
        }
        
        env {
          name  = "SECRET_KEY"
          value = random_password.secret_key.result
        }
        
        env {
          name  = "JWT_SECRET_KEY"
          value = random_password.jwt_secret.result
        }
        
        env {
          name  = "STORAGE_BUCKET"
          value = google_storage_bucket.bucket.name
        }
        
        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }
      }
      
      service_account_name = google_service_account.app.email
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_service.required_apis["run.googleapis.com"],
    google_project_iam_member.app_sa_roles
  ]
}

# Allow unauthenticated access to Cloud Run service
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.service.name
  location = google_cloud_run_service.service.location
  role     = "roles/run.invoker"
  member   = "allUsers"
  
  depends_on = [google_cloud_run_service.service]
}

# Outputs are defined in outputs.tf
