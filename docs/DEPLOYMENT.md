# Deployment Guide

This guide provides detailed instructions for deploying the Photo Portfolio application to various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Staging Environment](#staging-environment)
- [Production Environment](#production-environment)
- [Infrastructure as Code](#infrastructure-as-code)
- [CI/CD Pipeline](#cicd-pipeline)
- [Database Migrations](#database-migrations)
- [Monitoring Setup](#monitoring-setup)
- [Scaling](#scaling)
- [Disaster Recovery](#disaster-recovery)
- [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Tools Required

- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- [Google Cloud SDK](https://cloud.google.com/sdk/install)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) (for Kubernetes deployment)
- [Terraform](https://www.terraform.io/downloads.html) (for infrastructure as code)
- [Helm](https://helm.sh/docs/intro/install/) (for Kubernetes package management)

### Google Cloud Project Setup

1. Create a new Google Cloud Project or use an existing one
2. Enable the following APIs:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     sqladmin.googleapis.com \
     storage-component.googleapis.com \
     vision.googleapis.com \
     container.googleapis.com \
     iam.googleapis.com \
     cloudbuild.googleapis.com \
     containerregistry.googleapis.com \
     secretmanager.googleapis.com
   ```

3. Create a service account with appropriate permissions:
   ```bash
   gcloud iam service-accounts create photo-portfolio-sa \
     --display-name="Photo Portfolio Service Account"

   gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
     --member="serviceAccount:photo-portfolio-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
     --member="serviceAccount:photo-portfolio-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"

   gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
     --member="serviceAccount:photo-portfolio-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
     --role="roles/storage.admin"
   ```

4. Download the service account key:
   ```bash
   gcloud iam service-accounts keys create service-account-key.json \
     --iam-account=photo-portfolio-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com
   ```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Google Cloud SDK

### Backend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/photo-portfolio.git
   cd photo-portfolio/backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run database migrations:
   ```bash
   flask db upgrade
   ```

6. Start the development server:
   ```bash
   flask run
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Start the development server:
   ```bash
   npm start
   ```

### Docker Compose

For a complete local development environment with all services:

1. Navigate to the project root:
   ```bash
   cd ..
   ```

2. Start all services:
   ```bash
   docker-compose up --build
   ```

3. Access the application at http://localhost:3000

## Staging Environment

### Prerequisites

- Google Cloud Project with billing enabled
- Service account with necessary permissions
- Domain name (optional)

### Infrastructure Setup

1. Initialize Terraform:
   ```bash
   cd terraform/staging
   terraform init
   ```

2. Review the planned changes:
   ```bash
   terraform plan
   ```

3. Apply the changes:
   ```bash
   terraform apply
   ```

### Deploy Application

1. Build and push the Docker image:
   ```bash
   gcloud builds submit --config cloudbuild.staging.yaml
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy photo-portfolio-staging \
     --image gcr.io/$GOOGLE_CLOUD_PROJECT/photo-portfolio:staging \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars ENVIRONMENT=staging
   ```

## Production Environment

### Prerequisites

- Google Cloud Project with billing enabled
- Domain name with DNS access
- SSL certificate
- Monitoring and alerting configured

### Infrastructure Setup

1. Initialize Terraform:
   ```bash
   cd terraform/production
   terraform init
   ```

2. Review the planned changes:
   ```bash
   terraform plan
   ```

3. Apply the changes:
   ```bash
   terraform apply
   ```

### Deploy Application

1. Build and push the Docker image:
   ```bash
   gcloud builds submit --config cloudbuild.production.yaml
   ```

2. Deploy to Cloud Run:
   ```bash
   gcloud run deploy photo-portfolio-production \
     --image gcr.io/$GOOGLE_CLOUD_PROJECT/photo-portfolio:production \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars ENVIRONMENT=production
   ```

3. Set up a custom domain:
   ```bash
   gcloud beta run domain-mappings create --service photo-portfolio-production \
     --domain photos.example.com \
     --region us-central1
   ```

## Infrastructure as Code

The infrastructure is defined using Terraform in the `terraform/` directory:

```
terraform/
├── modules/           # Reusable modules
│   ├── cloud_sql/     # Cloud SQL module
│   ├── cloud_run/     # Cloud Run module
│   ├── storage/       # Cloud Storage module
│   └── vpc/           # VPC and networking module
├── staging/           # Staging environment
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
└── production/        # Production environment
    ├── main.tf
    ├── variables.tf
    └── outputs.tf
```

## CI/CD Pipeline

The CI/CD pipeline is defined in `.github/workflows/ci-cd.yml` and includes the following stages:

1. **Linting and Testing**
   - Run linters (black, isort, flake8, mypy)
   - Run unit and integration tests
   - Build and test Docker image

2. **Staging Deployment**
   - Deploy to staging environment
   - Run smoke tests
   - Run integration tests against staging

3. **Production Deployment** (manual approval required)
   - Deploy to production
   - Run smoke tests
   - Verify deployment

### Manual Deployment

For manual deployments, use the following commands:

```bash
# Build and push the Docker image
gcloud builds submit --config cloudbuild.$ENV.yaml

# Deploy to Cloud Run
gcloud run deploy photo-portfolio-$ENV \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/photo-portfolio:$ENV \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=$ENV
```

## Database Migrations

Database migrations are managed using Flask-Migrate. To create and apply migrations:

1. Create a new migration:
   ```bash
   flask db migrate -m "Description of the changes"
   ```

2. Review the generated migration file in `migrations/versions/`

3. Apply the migration:
   ```bash
   flask db upgrade
   ```

4. For production, run migrations as part of the deployment process

## Monitoring Setup

### Google Cloud Monitoring

1. Enable Cloud Monitoring API:
   ```bash
   gcloud services enable monitoring.googleapis.com
   ```

2. Set up dashboards for:
   - Application performance
   - Error rates
   - Request latency
   - Resource utilization

### Logging

1. Enable Cloud Logging API:
   ```bash
   gcloud services enable logging.googleapis.com
   ```

2. Set up log-based metrics for:
   - Error rates
   - Request volumes
   - User activity

### Alerting

1. Set up alerting policies for:
   - High error rates
   - High latency
   - Service unavailability
   - Resource constraints

## Scaling

### Horizontal Scaling

Cloud Run automatically scales the number of instances based on incoming requests. To configure:

```bash
gcloud run services update photo-portfolio-production \
  --min-instances 1 \
  --max-instances 10 \
  --concurrency 80 \
  --cpu 1 \
  --memory 512Mi
```

### Database Scaling

1. **Read Replicas**: Add read replicas for read-heavy workloads
2. **Vertical Scaling**: Increase machine type for more CPU/RAM
3. **Connection Pooling**: Configure connection pooling with Cloud SQL Proxy

## Disaster Recovery

### Backups

1. **Database Backups**:
   - Automated daily backups with 7-day retention
   - Point-in-time recovery enabled

2. **Storage Backups**:
   - Object versioning enabled on Cloud Storage buckets
   - Cross-region replication for critical data

### Recovery Procedures

1. **Database Recovery**:
   ```bash
   gcloud sql backups restore [BACKUP_ID] \
     --restore-instance=[TARGET_INSTANCE] \
     --backup-instance=[SOURCE_INSTANCE]
   ```

2. **Storage Recovery**:
   - Restore previous versions from Cloud Storage
   - Use object versioning to recover deleted files

## Rollback Procedures

### Application Rollback

1. Identify the previous working version:
   ```bash
   gcloud run revisions list --service photo-portfolio-production --region us-central1
   ```

2. Roll back to the previous version:
   ```bash
   gcloud run services update-traffic photo-portfolio-production \
     --to-revisions [REVISION_NAME]=100 \
     --region us-central1
   ```

### Database Rollback

1. Create a backup before making changes
2. If needed, restore from backup:
   ```bash
   gcloud sql backups restore [BACKUP_ID] \
     --restore-instance=[INSTANCE_NAME] \
     --backup-instance=[INSTANCE_NAME]
   ```

### Infrastructure Rollback

1. Revert Terraform changes:
   ```bash
   cd terraform/production
   terraform apply -target=module.specific_module
   ```

2. If necessary, roll back to a previous Terraform state:
   ```bash
   terraform state push terraform.tfstate.backup
   ```
