# Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "instance" {
  name             = var.instance_name
  database_version = var.database_version
  region           = var.region
  project          = var.project_id

  settings {
    tier              = var.tier
    activation_policy = "ALWAYS"
    availability_type = var.availability_type
    disk_size         = var.disk_size
    disk_type         = var.disk_type
    disk_autoresize   = true

    backup_configuration {
      enabled    = true
      start_time = "02:00"
      location   = var.backup_location
      backup_retention_settings {
        retained_backups = var.retained_backups
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_network
      require_ssl     = true
    }

    location_preference {
      zone = var.zone
    }

    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }
  }

  deletion_protection = var.deletion_protection
}

# Database
resource "google_sql_database" "database" {
  name     = var.database_name
  instance = google_sql_database_instance.instance.name
  project  = var.project_id
}

# User
resource "google_sql_user" "user" {
  name     = var.user_name
  instance = google_sql_database_instance.instance.name
  password = var.user_password
  project  = var.project_id
}

# SSL certificates
resource "google_sql_ssl_cert" "client_cert" {
  common_name = "client-cert"
  instance    = google_sql_database_instance.instance.name
  project     = var.project_id
}

# Export connection info
output "connection_name" {
  value = google_sql_database_instance.instance.connection_name
}

output "instance_ip" {
  value = google_sql_database_instance.instance.private_ip_address
}

output "instance_name" {
  value = google_sql_database_instance.instance.name
}
