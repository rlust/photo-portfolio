# 📷 Photo Portfolio Backend (FastAPI)

A high-performance, scalable backend for a photo portfolio application built with FastAPI, PostgreSQL, and Google Cloud Storage.

## ✨ Features

- **FastAPI** - Modern, fast (high-performance), web framework
- **PostgreSQL** - Robust relational database
- **SQLAlchemy** - ORM for database interactions
- **Alembic** - Database migrations
- **JWT Authentication** - Secure user authentication
- **Google Cloud Storage** - Scalable file storage
- **Redis** - Caching and background tasks
- **Docker** - Containerization for development and production
- **Pydantic** - Data validation and settings management
- **Testing** - Unit and integration tests with pytest
- **Linting & Formatting** - Black, isort, flake8, and mypy

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker 20.10+ and Docker Compose 2.10+
- Poetry 1.4+ (for local development)

## 🛠️ Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/photo-portfolio.git
cd photo-portfolio/backend
```

### 2. Set up environment variables

Copy the example environment file and update the values:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration.

### 3. Install dependencies

```bash
make install
```

### 4. Start development services

```bash
# Start all services (PostgreSQL, Redis, PgAdmin, etc.)
make docker-up

# Run database migrations
alembic upgrade head

# Start the development server
make dev
```

### 5. Access the application

- API: `http://localhost:8000`
- API Documentation (Swagger UI): `http://localhost:8000/docs`
- API Documentation (ReDoc): `http://localhost:8000/redoc`
- PgAdmin: `http://localhost:5050` (email: admin@example.com, password: admin)
- Adminer: `http://localhost:8080` (if enabled)

## 🧪 Testing

```bash
# Run all tests
make test

# Run tests with coverage report
pytest --cov=app --cov-report=html

# Run a specific test file
pytest tests/test_photos.py -v
```

## 🧹 Code Quality

```bash
# Run linters
make lint

# Format code
make format

# Run type checking
make typecheck
```

## 🐳 Docker Development

### Start services

```bash
make docker-up
```

### Stop services

```bash
make docker-down
```

### View logs

```bash
# All services
make docker-logs

# Specific service
make docker-logs service=app
```

### Database operations

```bash
# Open database shell
make db-shell

# Reset database (WARNING: deletes all data!)
make db-reset
```

## 🗃️ Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "Your migration message"
```

### Apply migrations

```bash
alembic upgrade head
```

## 🚀 Deployment

For detailed deployment instructions, see the [DEPLOYMENT.md](DEPLOYMENT.md) guide.

### Quick Start

1. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Deploy using the deployment script**:
   ```bash
   ./scripts/deploy.sh \
       --project-id your-project-id \
       --region us-central1 \
       --service-name photo-portfolio-backend \
       --db-instance your-db-instance-name
   ```

3. **Verify the deployment**:
   ```bash
   SERVICE_URL=$(gcloud run services describe photo-portfolio-backend \
       --platform managed \
       --region us-central1 \
       --format "value(status.url)")
   
   ./scripts/verify_deployment.sh --url $SERVICE_URL
   ```

4. **Trigger GCS reindexing** (if needed):
   ```bash
   ./scripts/reindex_gcs.sh --url $SERVICE_URL
   ```

### Available Deployment Scripts

- `scripts/deploy.sh` - Deploy the application to Google Cloud Run
- `scripts/verify_deployment.sh` - Verify the deployment and database population
- `scripts/reindex_gcs.sh` - Trigger GCS reindexing
- `scripts/dev.sh` - Development environment utilities

For more detailed instructions, configuration options, and troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md).

## 📚 API Documentation

### Authentication

Most endpoints require authentication. Include the JWT token in the `Authorization` header:

```
Authorization: Bearer your-jwt-token
```

### Available Endpoints

- `POST /api/auth/token` - Get access token
- `GET /api/health` - Health check
- `GET /api/photos` - List photos
- `POST /api/photos` - Upload a photo
- `GET /api/photos/{photo_id}` - Get photo details
- `PUT /api/photos/{photo_id}` - Update photo
- `DELETE /api/photos/{photo_id}` - Delete photo
- `GET /api/folders` - List folders
- `POST /api/folders` - Create folder
- `GET /api/folders/{folder_id}` - Get folder details
- `PUT /api/folders/{folder_id}` - Update folder
- `DELETE /api/folders/{folder_id}` - Delete folder

## 🏗️ Project Structure

```
backend/
├── app/                    # Application package
│   ├── __init__.py         # Package initialization
│   ├── main.py             # FastAPI application
│   ├── config.py           # Configuration settings
│   ├── database.py         # Database connection and session management
│   ├── models/             # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── photo.py        # Photo model
│   │   └── folder.py       # Folder model
│   ├── routes/             # API routes
│   │   ├── __init__.py
│   │   ├── photos.py       # Photo endpoints
│   │   └── folders.py      # Folder endpoints
│   └── services/           # Business logic
│       └── __init__.py
├── migrations/             # Database migrations
├── scripts/               # Utility scripts
│   ├── deploy.sh          # Deployment script
│   ├── dev.sh             # Development utilities
│   ├── reindex_gcs.sh     # GCS reindexing script
│   └── verify_deployment.sh # Deployment verification
├── tests/                 # Test suite
├── .env.example           # Example environment variables
├── .gitignore            # Git ignore rules
├── .dockerignore         # Docker ignore rules
├── .gcloudignore         # Google Cloud ignore rules
├── Dockerfile            # Production Dockerfile
├── docker-compose.yml    # Development docker-compose
├── docker-compose.prod.yml # Production docker-compose
├── pyproject.toml        # Project metadata and dependencies
└── README.md            # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - The modern, fast web framework for building APIs
- [SQLAlchemy](https://www.sqlalchemy.org/) - The Python SQL toolkit and ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Database migration tool
- [Google Cloud Platform](https://cloud.google.com/) - Cloud infrastructure and services

For support or questions, please contact [Your Name] at [Your Email].
