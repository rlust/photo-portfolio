# Application Features

This document lists all major functions and features of the Photo Portfolio application as of the latest deployment.

---

## Core Features

### 1. Gallery UI
- Displays all folders and images stored in Google Cloud Storage (GCS).
- Automatically updates when new images are uploaded or indexed.
- Clean, streamlined interface with minimal clutter.

### 2. Image Upload
- Upload images from the frontend UI to specific folders.
- Images are stored in GCS and registered in the backend database.
- Supports drag-and-drop and file picker uploads.

### 3. Folder Management
- Folders are auto-created when images are uploaded to new folders.
- All folders (even empty ones) are indexed and displayed in the gallery.

### 4. Image Serving & Caching
- Images are served directly from GCS URLs for performance and reliability.
- Backend provides metadata and links for each image.

### 5. Backend API Endpoints
- `/api/folders` — Returns all folders and their images as JSON.
- `/api/upload` — Accepts image uploads from the frontend.
- `/api/reindex-gcs` — Scans GCS and repopulates the backend DB with all folders and images (including empty folders).
- CORS enabled for all relevant endpoints.

### 6. Cloud Run Deployment
- Backend and frontend are containerized and deployed to Google Cloud Run.
- Automatic scaling and HTTPS support.
- Memory and resource limits configured for optimal performance.

### 7. Database Management
- Uses SQLite for backend metadata (folders, images, URLs, mimetypes).
- Database is automatically rebuilt using `/api/reindex-gcs` if lost or reset.

### 8. Error Handling & Robustness
- Handles CORS preflight and errors gracefully.
- Provides clear error messages for failed uploads or API calls.
- Logs and traces available in Cloud Run logs for debugging.

### 9. Security
- Only authenticated users can upload (if enabled in the frontend/backend).
- Publicly readable gallery and images (unless GCS permissions are restricted).

### 10. Extensibility
- Designed for easy addition of new endpoints or features (e.g., search, tagging, user accounts).

---

## Google Cloud Access Points

### 1. **Google Cloud Run**
- **Backend Service URL:**
  - Example: `https://photoportfolio-backend-839093975626.us-central1.run.app`
  - Hosts the Python/Flask backend API, automatically scales with demand, provides HTTPS, and handles incoming API requests from the frontend.
- **Frontend Service URL:**
  - Example: `https://photo-frontend-839093975626.us-central1.run.app`
  - Hosts the static frontend (React or similar), serving the gallery UI to users.

### 2. **Google Cloud Storage (GCS)**
- **Bucket:** `photoportfolio-uploads`
- **Function:** Stores all uploaded images and folders. The backend reads/writes image files here, and serves public URLs for direct image access.
- **Access Point:**
  - GCS Console: https://console.cloud.google.com/storage/browser/photoportfolio-uploads
  - Image URLs: `https://storage.googleapis.com/photoportfolio-uploads/folders/<folder>/<filename>`

### 3. **Google Cloud Build**
- **Function:** Builds and pushes Docker container images for backend/frontend to Google Container Registry.
- **Access Point:**
  - Cloud Build Console: https://console.cloud.google.com/cloud-build/builds

### 4. **Google Container Registry (GCR)**
- **Function:** Stores built Docker images for deployment to Cloud Run.
- **Access Point:**
  - Example: `gcr.io/photo-portfolio-459415/photo-backend:latest`

### 5. **Google IAM & Service Accounts**
- **Function:** Manages permissions for accessing GCS, Cloud Run, and other Google Cloud resources securely.
- **Access Point:**
  - IAM Console: https://console.cloud.google.com/iam-admin/iam

### 6. **Google Cloud Logs (Logging/Monitoring)**
- **Function:** Stores logs for backend/frontend Cloud Run services for debugging and monitoring.
- **Access Point:**
  - Logs Viewer: https://console.cloud.google.com/logs/viewer

---

## Advanced/Optional Features

- Support for sentence-transformers and image similarity search (if enabled).
- Nginx config for advanced frontend routing (if deployed).
- CI/CD ready for GitHub integration.

---

For any questions or to request new features, please contact the repository maintainer or open an issue on GitHub.
