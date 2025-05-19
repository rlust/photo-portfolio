# Photo Portfolio - Deployment Guide

This guide provides step-by-step instructions for deploying the Photo Portfolio backend to Google Cloud Run and setting up the necessary infrastructure.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Database Setup](#database-setup)
4. [Google Cloud Storage Setup](#google-cloud-storage-setup)
5. [Building and Deploying](#building-and-deploying)
6. [Verifying the Deployment](#verifying-the-deployment)
7. [Troubleshooting](#troubleshooting)
8. [Automated Deployment](#automated-deployment)

## Prerequisites

- Google Cloud account with billing enabled
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured
- [Docker](https://docs.docker.com/get-docker/) installed
- [Git](https://git-scm.com/) installed

## Google Cloud Setup

1. **Create a new project** or select an existing one:
   ```bash
   gcloud projects create photo-portfolio-12345 --name="Photo Portfolio"
   gcloud config set project photo-portfolio-12345
   ```

2. **Enable required APIs**:
   ```bash
   gcloud services enable \
       run.googleapis.com \
       sql-component.googleapis.com \
       sqladmin.googleapis.com \
       compute.googleapis.com \
       containerregistry.googleapis.com \
       cloudbuild.googleapis.com
   ```

3. **Set up authentication**:
   ```bash
   gcloud auth login
   gcloud auth configure-docker
   ```

## Database Setup

1. **Create a Cloud SQL instance**:
   ```bash
   gcloud sql instances create photo-portfolio-db \
       --database-version=POSTGRES_14 \
       --tier=db-f1-micro \
       --region=us-central1 \
       --root-password=your-root-password
   ```

2. **Create a database and user**:
   ```bash
   gcloud sql databases create photo_portfolio --instance=photo-portfolio-db
   gcloud sql users create photo_user --instance=photo-portfolio-db --password=your-strong-password
   ```

3. **Get the connection details**:
   ```bash
   gcloud sql instances describe photo-portfolio-db --format="value(connectionName)"
   ```
   Save the connection name (format: `project:region:instance`).

## Google Cloud Storage Setup

1. **Create a storage bucket**:
   ```bash
   gsutil mb -l us-central1 gs://photo-portfolio-uploads-12345
   ```

2. **Set up CORS configuration** (create a file named `cors.json`):
   ```json
   [
     {
       "origin": ["*"],
       "method": ["GET", "HEAD", "PUT", "POST", "DELETE"],
       "responseHeader": ["Content-Type", "Authorization", "Content-Length", "User-Agent", "x-goog-meta-filename"],
       "maxAgeSeconds": 3600
     }
   ]
   ```
   Then apply it:
   ```bash
   gsutil cors set cors.json gs://photo-portfolio-uploads-12345
   ```

## Building and Deploying

1. **Clone the repository** (if not already done):
   ```bash
   git clone https://github.com/yourusername/photo-portfolio.git
   cd photo-portfolio/backend
   ```

2. **Set up environment variables** in `.env`:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
   Make sure to set:
   ```
   ENVIRONMENT=production
   DB_HOST=/cloudsql/your-project-id:us-central1:photo-portfolio-db
   DB_NAME=photo_portfolio
   DB_USER=photo_user
   DB_PASSWORD=your-strong-password
   GCS_BUCKET=photo-portfolio-uploads-12345
   ```

3. **Deploy using the deployment script**:
   ```bash
   ./scripts/deploy.sh \
       --project-id your-project-id \
       --region us-central1 \
       --service-name photo-portfolio-backend \
       --db-instance photo-portfolio-db
   ```

   The script will:
   - Build and push the Docker image
   - Deploy to Cloud Run
   - Set up the necessary environment variables
   - Enable required APIs

## Verifying the Deployment

1. **Check the service URL**:
   ```bash
   gcloud run services describe photo-portfolio-backend \
       --platform managed \
       --region us-central1 \
       --format "value(status.url)"
   ```

2. **Run the verification script**:
   ```bash
   SERVICE_URL=$(gcloud run services describe photo-portfolio-backend \
       --platform managed \
       --region us-central1 \
       --format "value(status.url)")
   
   ./scripts/verify_deployment.sh --url $SERVICE_URL
   ```

3. **Trigger GCS reindexing** (if needed):
   ```bash
   ./scripts/reindex_gcs.sh --url $SERVICE_URL
   ```

## Troubleshooting

### Common Issues

1. **Database connection issues**:
   - Verify the Cloud SQL Proxy is running
   - Check the database user permissions
   - Ensure the database exists and is accessible

2. **GCS permissions**:
   - The service account needs `storage.objects.*` permissions on the bucket
   - Run: `gcloud storage buckets add-iam-policy-binding gs://your-bucket-name \
     --member="serviceAccount:your-service-account@your-project.iam.gserviceaccount.com" \
     --role="roles/storage.objectAdmin"`

3. **Container build failures**:
   - Check the Cloud Build logs
   - Ensure all dependencies are properly specified in `requirements.txt`

4. **Service not starting**:
   - Check the Cloud Run logs
   - Verify all environment variables are set correctly
   - Ensure the container is listening on the correct port (default: 8080)

## Automated Deployment

For CI/CD, you can use the following workflow:

1. **Create a Cloud Build trigger** that watches your repository
2. **Create a `cloudbuild.yaml`** in the root of your backend directory:
   ```yaml
   steps:
     # Build the container image
     - name: 'gcr.io/cloud-builders/docker'
       args: ['build', '-t', 'gcr.io/$PROJECT_ID/photo-portfolio-backend:$COMMIT_SHA', '.']
     
     # Push the container image to Container Registry
     - name: 'gcr.io/cloud-builders/docker'
       args: ['push', 'gcr.io/$PROJECT_ID/photo-portfolio-backend:$COMMIT_SHA']
     
     # Deploy container to Cloud Run
     - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
       entrypoint: gcloud
       args:
         - 'run'
         - 'deploy'
         - 'photo-portfolio-backend'
         - '--image'
         - 'gcr.io/$PROJECT_ID/photo-portfolio-backend:$COMMIT_SHA'
         - '--region'
         - 'us-central1'
         - '--platform'
         - 'managed'
         - '--allow-unauthenticated'
         - '--set-env-vars'
         - 'ENVIRONMENT=production,DB_HOST=/cloudsql/$PROJECT_ID:us-central1:photo-portfolio-db,DB_NAME=photo_portfolio,DB_USER=photo_user,DB_PASSWORD=$_DB_PASSWORD,GCS_BUCKET=photo-portfolio-uploads-12345'
         - '--add-cloudsql-instances'
         - '$PROJECT_ID:us-central1:photo-portfolio-db'
         - '--set-cloudsql-instances'
         - '$PROJECT_ID:us-central1:photo-portfolio-db'
   
   # Available secret variables
   substitutions:
     _DB_PASSWORD: 'your-db-password'
   
   # Images to push to Container Registry
   images:
     - 'gcr.io/$PROJECT_ID/photo-portfolio-backend:$COMMIT_SHA'
   ```

3. **Set up a trigger** in Cloud Build that runs on push to main/master

## Next Steps

- Set up a custom domain
- Configure monitoring and alerting
- Set up backup and disaster recovery
- Configure auto-scaling parameters
- Set up CI/CD for automated testing and deployment
