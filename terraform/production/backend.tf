# Using local backend for initial testing
# Uncomment and update the following to use GCS backend
# terraform {
#   backend "gcs" {
#     bucket = "photo-portfolio-tf-state"  # Replace with your bucket name
#     prefix = "production"
#   }
# }

# Using local backend for now
terraform {
  backend "local" {}
}
