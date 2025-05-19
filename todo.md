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
- [x] Fix Cloud SQL connection in Cloud Run using socket path
- [x] Schema updated to match application models
- [x] Initial test data populated
- [ ] Enable private IP (recommended)
- [ ] Set up automated backups
- [ ] Implement database migration system

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
- [x] Add comprehensive environment variable validation
- [x] Support for different environments (dev/staging/prod)
- [x] Add database connection pooling configuration
- [x] Implement proper logging configuration
- [x] Add feature flags system
- [x] Add CORS configuration via environment variables

### 2. Container Configuration
- [x] Multi-stage Dockerfile exists (backend/Dockerfile)
- [x] Basic health checks implemented
- [x] Set resource limits (configured in cloudbuild.yaml)
- [x] Add Secret Manager client library to Dockerfile
- [x] Configure proper logging in container
- [x] Add proper error handling for missing configurations
- [x] Set up proper file permissions in container
- [x] Implement lazy loading for external services (Secret Manager)
- [x] Fix database session handling in FastAPI
- [x] Add proper email validation dependencies
- [x] Fix non-root user configuration for better security
- [ ] Optimize container size for faster deployments
- [ ] Add resource usage monitoring

## CI/CD Pipeline

### 1. Cloud Build
- [x] Basic cloudbuild.yaml exists
- [ ] Set up build triggers (needs verification)
- [ ] Configure build steps:
  - [ ] Add pytest and test dependencies to Dockerfile
  - [ ] Create test configuration (pytest.ini, conftest.py)
  - [ ] Add test step to cloudbuild.yaml
  - [ ] Configure test coverage reporting
  - [x] Build container (configured)
  - [x] Push to Container Registry (configured)
  - [x] Deploy to Cloud Run (configured)
  - [ ] Add integration tests with Cloud SQL proxy
  - [ ] Add security scanning step (e.g., Snyk, Trivy)

### 2. Deployment Strategy
- [ ] Set up staging environment
  - [ ] Create separate Cloud Run service for staging
  - [ ] Configure staging database instance
  - [ ] Set up staging environment variables
  - [ ] Create separate storage bucket for staging
- [ ] Configure traffic splitting
  - [ ] Set up traffic management in Cloud Run
  - [ ] Implement canary deployment strategy
  - [ ] Configure percentage-based traffic routing
- [ ] Set up rollback procedures
  - [ ] Document manual rollback steps
  - [ ] Set up automated rollback on test failures
  - [ ] Configure health check timeouts

## Deployment

### 1. Initial Deployment
- [x] Deploy database migrations
- [x] Deploy backend service
- [x] Fix Cloud SQL connection issues
- [x] Update database schema to match application models
- [x] Implement proper error handling for Secret Manager
- [x] Fix database session handling in FastAPI
- [x] Populate initial database with test data
- [ ] Implement automated schema migrations
- [ ] Set up GCS storage integration for photos
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
- [x] Configuration System Refactored
- [ ] Testing
- [ ] Partially Deployed
- [ ] Fully Deployed

## Next Steps (Prioritized)

### 1. Unit Tests
- [x] Write tests for configuration system (85% coverage)
- [ ] Write tests for database models
- [ ] Write tests for API endpoints
- [ ] Write tests for utility functions
- [ ] Test authentication and authorization
- [ ] Test file uploads to mock GCS bucket

### 2. Test Configuration
- [x] Set up pytest with coverage reporting
- [x] Configure test database settings
- [x] Add test environment configuration
- [x] Implement test fixtures for database sessions
- [ ] Add integration tests for database operations

### 3. CI/CD Pipeline
- [x] Add test step to cloudbuild.yaml
- [x] Configure test coverage reporting (pytest-cov)
- [x] Set up coverage threshold (target: 80%)
- [x] Add automated testing in CI/CD pipeline
- [x] Set up test database in CI/CD pipeline
- [ ] Set up build notifications (Slack/Email)
- [ ] Add security scanning to pipeline

### 3. Staging Environment
- [ ] Deploy to staging environment
- [ ] Configure staging-specific settings
- [ ] Set up database migrations for staging
- [ ] Test API endpoints in staging

### 4. Documentation
- [ ] Document testing procedures
- [ ] Update deployment guide with new configuration
- [ ] Document environment setup for new developers
- [ ] Add troubleshooting guide

### 5. Security Hardening
- [ ] Move remaining secrets to Secret Manager
- [ ] Review and update IAM roles
- [ ] Set up private networking for Cloud SQL
- [ ] Configure VPC Service Controls

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
