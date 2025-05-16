# Photo Portfolio - Terraform Configuration

This directory contains the Terraform configuration for deploying the Photo Portfolio application to Google Cloud Platform (GCP).

## Prerequisites

1. Install [Terraform](https://www.terraform.io/downloads.html) (>= 1.0.0)
2. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. Authenticate with GCP:
   ```bash
   gcloud auth application-default login
   gcloud auth login
   ```
4. Enable the required GCP APIs:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     sqladmin.googleapis.com \
     compute.googleapis.com \
     vpcaccess.googleapis.com \
     secretmanager.googleapis.com \
     cloudbuild.googleapis.com \
     containerregistry.googleapis.com \
     servicenetworking.googleapis.com
   ```

## Directory Structure

```
terraform/
├── modules/               # Reusable modules
│   ├── cloud_run/         # Cloud Run service
│   ├── cloud_sql/         # Cloud SQL database
│   ├── cloud_storage/     # Cloud Storage bucket
│   └── vpc/               # VPC and networking
├── staging/               # Staging environment
│   ├── main.tf           # Main configuration
│   ├── variables.tf      # Input variables
│   └── outputs.tf        # Output values
├── production/           # Production environment (similar to staging)
├── versions.tf          # Terraform and provider versions
└── README.md            # This file
```

## Deployment

### Staging Environment

1. Navigate to the staging directory:
   ```bash
   cd terraform/staging
   ```

2. Create a `terraform.tfvars` file with your configuration:
   ```hcl
   project_id       = "your-project-id"
   database_password = "your-db-password"
   secret_key       = "your-secret-key"
   jwt_secret_key   = "your-jwt-secret-key"
   allowed_ssh_ips  = ["your-ip-address/32"]
   ```

3. Initialize Terraform:
   ```bash
   terraform init -backend-config="bucket=your-terraform-state-bucket" -backend-config="prefix=staging"
   ```

4. Review the execution plan:
   ```bash
   terraform plan
   ```

5. Apply the configuration:
   ```bash
   terraform apply
   ```

### Production Environment

The production environment is similar to staging but with more robust settings. Copy the staging directory to production and adjust the variables as needed.

## Modules

### Cloud SQL

Creates a Cloud SQL PostgreSQL instance with:
- Automated backups
- Private IP connectivity
- SSL enforcement
- Configurable machine type and storage

### Cloud Run

Deploys the application to Cloud Run with:
- Automatic scaling
- VPC connector for private connectivity
- Secret management integration
- Custom domain support

### Cloud Storage

Creates a Cloud Storage bucket for media files with:
- Versioning
- Lifecycle rules
- CORS configuration
- IAM permissions

### VPC

Sets up a VPC with:
- Private subnet
- Cloud NAT for outbound connectivity
- VPC connector for Serverless VPC Access
- Firewall rules

## Secrets Management

Sensitive values like database passwords and API keys are managed using Secret Manager. The Terraform configuration creates the necessary secrets and grants the Cloud Run service account access to them.

## State Management

Terraform state is stored in a Google Cloud Storage bucket. The bucket name is configured during initialization.

## Best Practices

1. **Use workspaces**: Create separate workspaces for different environments
2. **Enable versioning**: On the GCS bucket used for state storage
3. **Use variables**: Never hardcode sensitive values
4. **Review plans**: Always review the plan before applying changes
5. **Lock state**: Use remote state locking to prevent concurrent modifications

## Cleanup

To destroy all resources created by Terraform:

```bash
terraform destroy
```

**Warning**: This will permanently delete all resources. Make sure you have backups of any important data.
