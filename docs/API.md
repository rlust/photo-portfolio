# API Reference

## Table of Contents

- [Authentication](#authentication)
- [Users](#users)
- [Photos](#photos)
- [Albums](#albums)
- [Search](#search)
- [Tags](#tags)
- [Analytics](#analytics)

## Authentication

### Register a New User

```http
POST /api/auth/register
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response:**

```json
{
  "message": "User registered successfully",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "created_at": "2023-01-01T00:00:00Z"
  }
}
```

### Login

```http
POST /api/auth/login
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

## Photos

### Upload Photos

```http
POST /api/photos/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>
```

**Form Data:**

- `files`: (required) One or more image files
- `album_id`: (optional) ID of the album to add photos to
- `title`: (optional) Title for the photo(s)
- `description`: (optional) Description for the photo(s)
- `tags`: (optional) Comma-separated list of tags
- `is_public`: (optional) Boolean, default: false

**Response:**

```json
{
  "message": "Photos uploaded successfully",
  "photos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Beach Sunset",
      "url": "https://storage.googleapis.com/photo-portfolio-uploads/...",
      "thumbnail_url": "https://storage.googleapis.com/photo-portfolio-uploads/...",
      "width": 1920,
      "height": 1080,
      "size": 1024000,
      "mime_type": "image/jpeg",
      "created_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

### Get Photo Details

```http
GET /api/photos/{photo_id}
Authorization: Bearer <token>
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Beach Sunset",
  "description": "Beautiful sunset at the beach",
  "url": "https://storage.googleapis.com/photo-portfolio-uploads/...",
  "width": 1920,
  "height": 1080,
  "size": 1024000,
  "mime_type": "image/jpeg",
  "is_public": false,
  "tags": ["beach", "sunset", "vacation"],
  "exif": {
    "camera": "Canon EOS 5D Mark IV",
    "lens": "EF24-70mm f/2.8L II USM",
    "focal_length": "50mm",
    "aperture": "f/8",
    "shutter_speed": "1/250s",
    "iso": 100,
    "taken_at": "2023-06-15T18:30:00Z"
  },
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

## Search

### Search Photos

```http
GET /api/search/photos?q=beach&limit=20&offset=0
Authorization: Bearer <token>
```

**Query Parameters:**

- `q`: (optional) Search query string
- `tags`: (optional) Comma-separated list of tags
- `album_id`: (optional) Filter by album ID
- `user_id`: (optional) Filter by user ID
- `start_date`: (optional) Filter by start date (ISO 8601)
- `end_date`: (optional) Filter by end date (ISO 8601)
- `limit`: (optional) Number of results per page (default: 20)
- `offset`: (optional) Pagination offset (default: 0)
- `sort`: (optional) Sort field (created_at, -created_at, title, -title)

**Response:**

```json
{
  "total": 42,
  "offset": 0,
  "limit": 20,
  "photos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Beach Sunset",
      "url": "https://storage.googleapis.com/photo-portfolio-uploads/...",
      "thumbnail_url": "https://storage.googleapis.com/photo-portfolio-uploads/...",
      "width": 1920,
      "height": 1080,
      "created_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

## Error Responses

### 400 Bad Request

```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "details": {
    "email": ["Not a valid email address"],
    "password": ["Password must be at least 8 characters long"]
  }
}
```

### 401 Unauthorized

```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing authentication token"
}
```

### 403 Forbidden

```json
{
  "error": "Forbidden",
  "message": "You don't have permission to access this resource"
}
```

### 404 Not Found

```json
{
  "error": "NotFound",
  "message": "The requested resource was not found"
}
```

### 500 Internal Server Error

```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred"
}
```
