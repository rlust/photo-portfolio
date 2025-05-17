# Google Cloud Deployment Plan

## Overview
This document outlines the steps required to deploy the Photo Portfolio application to Google Cloud Platform (GCP).

## Prerequisites
- [x] Google Cloud Project created (referenced in cloudbuild.yaml)
- [ ] Billing enabled (needs verification)
- [x] gcloud CLI installed and authenticated (assumed for local development)
- [x] Required APIs enabled:
  - [x] Cloud Run API (referenced in cloudbuild.yaml)
  - [x] Cloud SQL Admin API (referenced in cloudbuild.yaml)
  - [x] Cloud Storage API (referenced in cloudbuild.yaml)
  - [x] Cloud Build API (using cloudbuild.yaml)
  - [x] Secret Manager API (implemented)
  - [x] Container Registry API (implied by cloudbuild.yaml)

## Infrastructure Setup

### 1. Cloud SQL (PostgreSQL)
- [x] Cloud SQL instance configured (referenced in cloudbuild.yaml as `photoportfolio-db`)
- [x] Database and user configured (user: `rlust`, db: `photoportfolio` in cloudbuild.yaml)
- [x] Basic connection settings configured
- [ ] Enable private IP (recommended)
- [ ] Set up automated backups

### 2. Cloud Storage
- [x] Storage bucket configured (`photoportfolio-uploads` in cloudbuild.yaml)
- [ ] Configure CORS policy
- [ ] Set up lifecycle rules
- [ ] Configure IAM permissions

### 3. Secret Manager
- [x] Store database credentials (moved from cloudbuild.yaml to Secret Manager)
- [x] Store application secret key
- [x] Implement secret retrieval in application code
- [ ] Set up secret rotation policy
- [ ] Document secret management process (partially done in SECRETS.md)

## Application Configuration

### 1. Environment Variables
- [x] Environment configuration using pydantic (config.py)
- [x] Move hardcoded values to environment variables:
  - [x] Database connection settings (moved to Secret Manager)
  - [x] Storage bucket name (in cloudbuild.yaml)
  - [x] API keys (moved to Secret Manager)
  - [x] Authentication secrets (moved to Secret Manager)
- [x] Implement secret fallback mechanism for local development

### 2. Container Configuration
- [x] Multi-stage Dockerfile exists (backend/Dockerfile)
- [x] Basic health checks (needs verification)
- [x] Set resource limits (configured in cloudbuild.yaml)
- [x] Add Secret Manager client library to Dockerfile

## CI/CD Pipeline

### 1. Cloud Build
- [x] Basic cloudbuild.yaml exists
- [ ] Set up build triggers (needs verification)
- [ ] Configure build steps:
  - [ ] Run tests (missing in pipeline)
  - [x] Build container (configured)
  - [x] Push to Container Registry (configured)
  - [x] Deploy to Cloud Run (configured)

### 2. Deployment Strategy
- [ ] Set up staging environment (needs implementation)
- [ ] Configure traffic splitting (needs implementation)
- [ ] Set up rollback procedures (needs implementation)

## Deployment

### 1. Initial Deployment
- [ ] Deploy database migrations
- [ ] Deploy backend service
- [ ] Configure domain and SSL
- [ ] Set up monitoring and logging

### 2. Post-Deployment
- [ ] Verify all services are running
- [ ] Test file uploads
- [ ] Test database connectivity
- [ ] Verify API endpoints

## Monitoring and Maintenance
- [ ] Set up Cloud Monitoring
- [ ] Configure alerts
- [ ] Set up logging exports
- [ ] Schedule regular backups

## Security
- [ ] Enable VPC Service Controls
- [x] Configure IAM roles and permissions
- [ ] Set up audit logging
- [ ] Enable Data Loss Prevention (DLP) if needed

## Optimization
- [ ] Configure CDN for static assets
- [ ] Set up caching
- [ ] Optimize database indexes
- [ ] Configure auto-scaling

## Current Status
- [x] Planning
- [x] Initial Implementation
- [ ] Testing
- [ ] Partially Deployed
- [ ] Fully Deployed

## Next Steps
1. **Security Hardening**:
   - Move sensitive data from cloudbuild.yaml to Secret Manager
   - Implement proper IAM roles and permissions
   - Set up private networking for Cloud SQL

2. **Testing**:
   - Add automated tests to the CI/CD pipeline
   - Set up a staging environment
   - Test database migrations

3. **Monitoring**:
   - Set up Cloud Monitoring
   - Configure alerts
   - Set up logging exports

4. **Optimization**:
   - Configure CDN for static assets
   - Set up caching
   - Optimize database indexes

5. **Documentation**:
   - Document deployment process
   - Create runbooks for common operations
   - Document backup and recovery procedures

## Notes
- Update this document as the deployment progresses
- Check off completed items
- Add any additional tasks as needed
