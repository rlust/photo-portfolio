# 📷 Photo Portfolio

A modern, scalable, and secure web application for photographers and visual artists to upload, organize, search, and manage their images online. Built with Flask, React, Google Cloud Platform, and designed with performance and security in mind.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

## 🌟 Features

### 📸 Image Management
- **Drag & Drop Upload** - Easily upload single or multiple images
- **Folder Organization** - Organize photos into custom folders
- **Bulk Actions** - Select and manage multiple images at once
- **High-Resolution Support** - Handles high-resolution images efficiently

### 🔍 Advanced Search
- **Semantic Search** - Find images using natural language queries
- **Tagging System** - Add custom tags to images for better organization
- **Metadata Search** - Search by EXIF data, creation date, and more
- **Visual Search** - Find similar images using AI-powered visual search

### 🛡 Security
- **Authentication** - Secure user authentication with JWT
- **Authorization** - Role-based access control (RBAC)
- **Data Encryption** - At-rest and in-transit encryption
- **Audit Logging** - Comprehensive activity logging

### ☁️ Cloud Integration
- **Google Cloud Storage** - Scalable and durable storage
- **Cloud Vision API** - Automatic image analysis and tagging
- **Cloud SQL** - Managed PostgreSQL database
- **Cloud Run** - Serverless deployment

### 🚀 Performance
- **Responsive Design** - Works on desktop and mobile devices
- **Image Optimization** - Automatic resizing and compression
- **Caching** - Client and server-side caching for faster load times
- **CDN** - Global content delivery for fast image loading

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Google Cloud SDK
- A Google Cloud Platform account

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/photo-portfolio.git
   cd photo-portfolio
   ```

2. **Set up the backend**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your configuration
   poetry install
   poetry run flask db upgrade
   poetry run flask run
   ```

3. **Set up the frontend**
   ```bash
   cd ../frontend
   cp .env.example .env
   # Edit .env with your configuration
   npm install
   npm start
   ```

4. **Run with Docker**
   ```bash
   docker-compose up --build
   ```

### Production Deployment

1. **Set up Google Cloud Project**
   ```bash
   gcloud projects create photo-portfolio-12345
   gcloud config set project photo-portfolio-12345
   ```

2. **Enable required APIs**
   ```bash
   gcloud services enable \
     run.googleapis.com \
     sqladmin.googleapis.com \
     storage-component.googleapis.com \
     vision.googleapis.com
   ```

3. **Deploy the application**
   ```bash
   # Deploy backend to Cloud Run
   gcloud run deploy photo-portfolio-backend \
     --source backend \
     --platform managed \
     --region us-central1

   # Deploy frontend to Firebase Hosting
   cd frontend
   firebase deploy --only hosting
   ```

## 🛠 API Documentation

### Authentication

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

### Upload Images

```http
POST /api/photos/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

{
  "folder": "vacation-2023",
  "files": [binary image data]
}
```

### Search Photos

```http
GET /api/photos/search?q=beach&limit=20&offset=0
Authorization: Bearer <token>
```

## 📚 Documentation

For detailed documentation, please see:

- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Development Guide](docs/DEVELOPMENT.md)

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - The web framework used
- [React](https://reactjs.org/) - Frontend library
- [Google Cloud Platform](https://cloud.google.com/) - Cloud infrastructure
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Poetry](https://python-poetry.org/) - Dependency management

---

<div align="center">
  Made with ❤️ by Your Name
</div>

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
