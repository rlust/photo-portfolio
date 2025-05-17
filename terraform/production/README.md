# Photo Portfolio - Production Infrastructure

This directory contains the Terraform configuration for deploying the Photo Portfolio application to a production environment on Google Cloud Platform (GCP).

## Prerequisites

1. [Terraform](https://www.terraform.io/downloads.html) (>= 1.0.0)
2. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. A GCP project with billing enabled
4. Required APIs enabled (they will be enabled automatically if you have the necessary permissions)

## Setup

1. **Copy the example variables file** and update it with your values:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Authenticate with GCP**:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

4. **Review the execution plan**:
   ```bash
   terraform plan
   ```

5. **Apply the configuration**:
   ```bash
   terraform apply
   ```

## Project Structure

- `main.tf`: Main configuration file containing resource definitions
- `variables.tf`: Input variables for the configuration
- `outputs.tf`: Output values from the infrastructure
- `providers.tf`: Provider configurations
- `backend.tf`: Backend configuration for storing Terraform state
- `terraform.tfvars.example`: Example variable values (copy to `terraform.tfvars` and customize)

## Components

This Terraform configuration will create the following resources:

- **VPC Network**: A dedicated VPC for the application
- **Cloud SQL**: PostgreSQL database instance
- **Cloud Storage**: Bucket for storing media files
- **Cloud Run**: Serverless container for the application
- **Service Accounts**: IAM roles and permissions
- **Secret Manager**: For storing sensitive configuration

## Security Notes

- Never commit sensitive values (passwords, API keys) to version control
- Use `terraform.tfvars` for local development and CI/CD variables for production
- Review IAM permissions to ensure the principle of least privilege

## Managing Secrets

Sensitive values like database passwords and API keys are managed using Google Secret Manager. The Terraform configuration will create the necessary secrets and grant the Cloud Run service account access to them.

## Updating the Infrastructure

To make changes to the infrastructure:

1. Update the Terraform configuration files
2. Review the changes:
   ```bash
   terraform plan
   ```
3. Apply the changes:
   ```bash
   terraform apply
   ```

## Destroying Resources

To tear down all resources created by this configuration:

```bash
terraform destroy
```

**Warning**: This will delete all resources managed by this Terraform configuration, including the database and all stored data.
