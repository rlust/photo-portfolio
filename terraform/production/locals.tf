locals {
  # Common tags to be applied to all resources
  common_tags = {
    Environment = "production"
    Project     = "photo-portfolio"
    ManagedBy   = "terraform"
    Owner       = "devops"
    CostCenter  = "marketing"
  }
  
  # Naming conventions
  name_prefix = "prod-photo-portfolio"
  
  # Resource naming
  resource_names = {
    vpc            = "${local.name_prefix}-vpc"
    cloud_sql      = "${local.name_prefix}-sql"
    cloud_run      = "${local.name_prefix}-api"
    storage_bucket = "${var.project_id}-${local.name_prefix}-storage"
    service_account = "${local.name_prefix}-sa"
  }
  
  # Network configuration
  network_config = {
    vpc_cidr             = var.subnet_cidr
    private_service_cidr = "192.168.0.0/16"
    vpc_connector_cidr  = "10.8.0.0/28"
  }
  
  # Database configuration
  database_config = {
    name     = var.database_name
    username = var.database_user
    password = var.database_password
    port     = 5432
  }
  
  # Cloud Run configuration
  cloud_run_config = {
    min_instances = 1
    max_instances = 5
    cpu           = "2000m"
    memory        = "2Gi"
    concurrency   = 80
  }
  
  # Environment variables for the application
  app_environment = {
    ENVIRONMENT          = "production"
    DEBUG                = "False"
    LOG_LEVEL            = "INFO"
    SECRET_KEY           = var.secret_key
    JWT_SECRET_KEY       = var.jwt_secret_key
    ALLOWED_HOSTS        = "*"
    CSRF_TRUSTED_ORIGINS = "https://${var.domain_name}"
  }
}
