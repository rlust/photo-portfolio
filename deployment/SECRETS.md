# Secrets Management

This document outlines how to manage secrets for the Photo Portfolio application using Google Cloud Secret Manager.

## Prerequisites

1. Google Cloud SDK installed and configured
2. Appropriate permissions to create and manage secrets in the Google Cloud project
3. Python 3.7+ with pip

## Setting Up Secrets

### 1. Install Dependencies

```bash
cd deployment/scripts
pip install -r requirements.txt
```

### 2. Set Up Secrets

Run the setup script to create the necessary secrets in Secret Manager:

```bash
python setup_secrets.py --project-id YOUR_PROJECT_ID
```

The script will guide you through:
1. Setting up database credentials
2. Generating and storing an application secret key

### 3. Grant Access to Secrets

Grant the Cloud Run service account access to the secrets:

```bash
# Replace YOUR_PROJECT_ID with your actual project ID
SERVICE_ACCOUNT="photo-portfolio-sa@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud secrets add-iam-policy-binding database-credentials \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding app-secret-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

## Environment Variables

The application uses the following environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `USE_SECRET_MANAGER` | Yes | Set to `true` to enable Secret Manager integration |
| `GOOGLE_CLOUD_PROJECT` | Yes | Google Cloud project ID |
| `GCS_BUCKET` | Yes | Google Cloud Storage bucket for uploads |
| `DB_INSTANCE` | Yes | Cloud SQL instance name |
| `DB_REGION` | Yes | Cloud SQL region |

## Secrets Reference

### Database Credentials
- **Secret ID**: `database-credentials`
- **Format**: JSON
- **Content**:
  ```json
  {
    "DB_USER": "database_username",
    "DB_PASSWORD": "database_password",
    "DB_HOST": "database_host",
    "DB_PORT": "5432",
    "DB_NAME": "database_name"
  }
  ```

### Application Secret Key
- **Secret ID**: `app-secret-key`
- **Format**: String
- **Content**: A secure random string used for session encryption and other security features

## Updating Secrets

To update a secret:

1. Go to the [Secret Manager](https://console.cloud.google.com/security/secret-manager) in the Google Cloud Console
2. Select the secret you want to update
3. Click "+ NEW VERSION"
4. Enter the new secret value
5. Click "ADD NEW VERSION"

## Local Development

For local development, create a `.env` file in the `backend` directory with the following variables:

```env
# Database settings
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=photo_portfolio

# App settings
SECRET_KEY=your_secret_key
GCS_BUCKET=your-bucket-name
```

## Troubleshooting

### Secret Access Issues

If the application can't access the secrets, verify that:

1. The Cloud Run service account has the `roles/secretmanager.secretAccessor` role
2. The secret names match exactly
3. The secret exists in the same project as the Cloud Run service

### Connection Issues

If you're having database connection issues:

1. Verify the database credentials in Secret Manager
2. Check that the Cloud SQL Proxy is running (for local development)
3. Verify network connectivity to the database

## Security Best Practices

1. Never commit secrets to version control
2. Use the principle of least privilege when granting access to secrets
3. Rotate secrets regularly
4. Monitor secret access using Cloud Audit Logs
