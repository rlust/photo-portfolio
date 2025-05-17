output "service_url" {
  description = "The URL of the Cloud Run service"
  value       = google_cloud_run_service.service.status[0].url
}

output "service_name" {
  description = "The name of the Cloud Run service"
  value       = google_cloud_run_service.service.name
}

output "service_id" {
  description = "The unique identifier of the Cloud Run service"
  value       = google_cloud_run_service.service.id
}

output "domain_mapping" {
  description = "The domain mapping configuration"
  value       = var.domain_name != "" ? google_cloud_run_domain_mapping.domain_mapping[0] : null
}
