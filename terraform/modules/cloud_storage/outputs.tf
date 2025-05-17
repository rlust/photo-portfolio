output "bucket_name" {
  description = "The name of the bucket"
  value       = google_storage_bucket.bucket.name
}

output "bucket_self_link" {
  description = "The URI of the created resource"
  value       = google_storage_bucket.bucket.self_link
}

output "bucket_url" {
  description = "The base URL of the bucket, in the format gs://<bucket-name>"
  value       = "gs://${google_storage_bucket.bucket.name}"
}

output "bucket_location" {
  description = "The location of the bucket"
  value       = google_storage_bucket.bucket.location
}

output "bucket_storage_class" {
  description = "The storage class of the bucket"
  value       = google_storage_bucket.bucket.storage_class
}

output "bucket_versioning" {
  description = "The versioning configuration of the bucket"
  value       = google_storage_bucket.bucket.versioning[0].enabled
}
