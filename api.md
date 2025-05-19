# API Documentation

This document describes all available API endpoints for the Photo Portfolio backend, including usage, parameters, and example requests/responses.

---

## 1. `GET /api/folders`
**Description:**
Returns a JSON object listing all folders and their images.

**Usage:**
```
GET /api/folders
```
**Response Example:**
```json
{
  "vacation": [
    {
      "filename": "beach.jpg",
      "url": "https://storage.googleapis.com/photoportfolio-uploads/folders/vacation/beach.jpg",
      "mimetype": "image/jpeg"
    }
  ],
  "family": [ ... ]
}
```

---

## 2. `POST /api/upload`
**Description:**
Uploads an image to a specified folder.

**Usage:**
- Content-Type: `multipart/form-data`
- Fields:
  - `file`: The image file
  - `folder`: (string) The folder name

**Example (curl):**
```
curl -X POST https://<backend-url>/api/upload \
  -F "file=@/path/to/image.jpg" \
  -F "folder=vacation"
```
**Response Example:**
```json
{"status": "ok", "folder": "vacation", "filename": "image.jpg"}
```

---

## 3. `POST /api/reindex-gcs`
**Description:**
Scans the Google Cloud Storage bucket and repopulates the backend database with all folders (including empty ones) and images.

**Usage:**
```
POST /api/reindex-gcs
```
**Response Example:**
```json
{"status": "ok", "folders": ["vacation", "family"], "indexed_files": 12}
```

---

## 4. CORS & Preflight
- All endpoints support CORS and handle preflight (`OPTIONS`) requests.

---

## 5. Error Handling
- All endpoints return JSON error messages with HTTP status codes.
- Example error response:
```json
{"error": "Invalid request", "trace": "..."}
```

---

## 6. Additional Notes
- All API endpoints are accessible at your deployed backend URL (e.g., `https://photoportfolio-backend-839093975626.us-central1.run.app`).
- For questions or feature requests, see the project README or contact the maintainer.
