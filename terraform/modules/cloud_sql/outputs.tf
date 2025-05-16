output "connection_name" {
  description = "The connection name of the Cloud SQL instance"
  value       = google_sql_database_instance.instance.connection_name
}

output "private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.instance.private_ip_address
}

output "public_ip" {
  description = "The public IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.instance.public_ip_address
}

output "instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = google_sql_database_instance.instance.name
}

output "database_name" {
  description = "The name of the default database"
  value       = google_sql_database.database.name
}

output "user_name" {
  description = "The name of the default user"
  value       = google_sql_user.user.name
}
