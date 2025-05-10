# PhotoPortfolio

A modern web application for photographers and visual artists to upload, organize, search, and manage their images online. Inspired by Zenfolio, built with Flask, React, Google Cloud Storage, and SQLite.

---

## Features

### 📸 Image Upload & Organization
- Upload single images or groups of images to named folders.
- Organize images into folders for easy management.
- Images are stored persistently in Google Cloud Storage (GCS).

### 🗂 Folder Management
- View all folders and their images in a gallery UI.
- Delete individual images from a folder.
- Delete an entire folder and all images within it.

### 🔍 Search & Filter
- Search images by name (substring match), folder, mimetype, or upload date range.
- See search results in a gallery view with image metadata.
- Clear search to return to normal folder browsing.

### 🗃 Persistent Metadata
- All folder and image metadata is stored in a local SQLite database for advanced queries.
- Easily adaptable to use Firestore or Cloud SQL for production.

### ☁️ Google Cloud Integration
- Images are uploaded to and served from a public GCS bucket (`photoportfolio-uploads`).
- Backend auto-creates the GCS bucket if it doesn't exist.
- All images are accessible via public URLs.

### 🛡 Security & Roles
- Cloud Run service account must have Storage Object Admin for the GCS bucket.
- All image URLs are public for easy access and sharing.

---

## API Endpoints

### Image Upload
- `POST /api/upload` — Upload images to a folder (multipart form-data)

### Folder & Image Management
- `GET /api/folders` — List all folders with their images
- `DELETE /api/folder/<folder>` — Delete a folder and all its images
- `DELETE /api/folder/<folder>/<image>` — Delete a specific image from a folder

### Search & Filtering
- `GET /api/photos/search?name=&folder=&mimetype=&date_from=&date_to=` — Search images by filters
- `GET /api/folders/search?name=` — Search folders by name substring

### Users (Demo)
- `GET /api/users` — List users (demo endpoint)

---

## Frontend Functionality
- Upload images via drag-and-drop or file picker
- Browse folders and images in a responsive gallery
- Delete images or entire folders with confirmation
- Search/filter images with instant results
- All actions update the UI automatically

---

## Running Locally

1. **Backend:**
   - Python 3.11+, Flask, Flask-CORS, google-cloud-storage, sqlite3
   - Run: `python app.py` in `/backend`
2. **Frontend:**
   - React (create-react-app)
   - Run: `npm install && npm start` in `/frontend`

---

## Deployment
- Both backend and frontend are deployable to Google Cloud Run.
- Images are stored in GCS; metadata in SQLite (or Firestore for production).

---

## Roadmap & Ideas
- User authentication (OAuth, etc.)
- Image sharing links with permissions
- Tagging and advanced metadata
- Integration with Firestore or Cloud SQL
- Improved UI/UX and mobile experience

---

## License
MIT
