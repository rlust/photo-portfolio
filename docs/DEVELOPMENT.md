# Development Guide

This guide provides detailed instructions for setting up and working with the Photo Portfolio application in a development environment.

## Table of Contents

- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [API Development](#api-development)
- [Frontend Development](#frontend-development)
- [Database](#database)
- [Authentication](#authentication)
- [Environment Variables](#environment-variables)
- [Debugging](#debugging)
- [Performance Optimization](#performance-optimization)
- [Security](#security)
- [Contributing](#contributing)

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Google Cloud SDK (for deployment)
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/photo-portfolio.git
   cd photo-portfolio
   ```

2. **Set up the backend**
   ```bash
   # Navigate to backend directory
   cd backend
   
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your configuration
   
   # Run database migrations
   flask db upgrade
   
   # Start the development server
   flask run
   ```

3. **Set up the frontend**
   ```bash
   # Navigate to frontend directory
   cd ../frontend
   
   # Install dependencies
   npm install
   
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your configuration
   
   # Start the development server
   npm start
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - API Documentation: http://localhost:5000/api/docs

## Project Structure

### Backend Structure

```
backend/
├── app/                      # Main application package
│   ├── api/                  # API routes
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── photos.py         # Photo management endpoints
│   │   ├── albums.py         # Album management endpoints
│   │   ├── search.py         # Search endpoints
│   │   └── users.py          # User management endpoints
│   │
│   ├── models/             # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── photo.py
│   │   ├── album.py
│   │   └── tag.py
│   │
│   ├── services/           # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── photo_service.py
│   │   ├── storage_service.py
│   │   └── search_service.py
│   │
│   ├── utils/              # Utility functions
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── validators.py
│   │
│   ├── __init__.py         # Application factory
│   └── extensions.py       # Flask extensions
│
├── migrations/            # Database migrations
├── tests/                  # Test suite
├── .env.example           # Example environment variables
├── .gitignore
├── .dockerignore
├── Dockerfile             # Production Dockerfile
├── docker-compose.yml     # Local development
├── gunicorn.conf.py       # Gunicorn configuration
├── manage.py              # CLI commands
└── requirements.txt       # Dependencies
```

### Frontend Structure

```
frontend/
├── public/               # Static files
│   ├── index.html
│   └── assets/
│
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── common/       # Common components (buttons, inputs, etc.)
│   │   ├── layout/       # Layout components (header, footer, etc.)
│   │   ├── photos/       # Photo-related components
│   │   ├── albums/       # Album-related components
│   │   └── auth/         # Authentication components
│   │
│   ├── pages/          # Page components
│   │   ├── Home/
│   │   ├── Login/
│   │   ├── Photos/
│   │   ├── Albums/
│   │   └── Settings/
│   │
│   ├── services/        # API service layer
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── photos.ts
│   │   └── albums.ts
│   │
│   ├── store/          # State management
│   │   ├── index.ts
│   │   ├── auth/
│   │   └── photos/
│   │
│   ├── types/           # TypeScript type definitions
│   ├── utils/           # Utility functions
│   ├── App.tsx
│   ├── index.tsx
│   └── routes.tsx
│
├── .env.example
├── package.json
├── tsconfig.json
└── README.md
```

## Development Workflow

### Git Workflow

We follow the [GitHub Flow](https://guides.github.com/introduction/flow/) workflow:

1. **Create a branch** for your feature or bugfix
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-number-description
   ```

2. **Make your changes** and commit them with a descriptive message
   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   ```

3. **Push your changes** to the remote repository
   ```bash
   git push -u origin feature/your-feature-name
   ```

4. **Create a pull request** (PR) on GitHub
   - Request a code review from at least one team member
   - Address any feedback and push updates to your branch
   - Once approved, squash and merge your PR

### Code Style

- **Python**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with a line length of 100 characters
- **JavaScript/TypeScript**: Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- **CSS/SCSS**: Follow [BEM methodology](http://getbem.com/)

### Pre-commit Hooks

We use pre-commit hooks to enforce code quality. Install them with:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install
```

The hooks will run automatically on each commit and check for:
- Code formatting (black, isort)
- Linting (flake8, eslint)
- Type checking (mypy, TypeScript)
- Security vulnerabilities

## Testing

### Running Tests

#### Backend Tests

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_auth.py

# Run a specific test
pytest tests/test_auth.py::test_user_registration

# Run tests with coverage
pytest --cov=app --cov-report=term-missing
```

#### Frontend Tests

```bash
# Run unit tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage
```

### Writing Tests

#### Backend Tests

- Place test files in the `tests/` directory
- Use `pytest` fixtures for test setup and teardown
- Follow the "Arrange-Act-Assert" pattern
- Use factories (e.g., `factory_boy`) for test data

Example test:

```python
def test_user_registration(client, db):
    # Arrange
    user_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User"
    }
    
    # Act
    response = client.post("/api/auth/register", json=user_data)
    
    # Assert
    assert response.status_code == 201
    assert "id" in response.json
    assert response.json["email"] == user_data["email"]
    assert "password" not in response.json
```

#### Frontend Tests

- Use React Testing Library for component testing
- Mock API calls with MSW (Mock Service Worker)
- Test user interactions and component rendering
- Follow the "Given-When-Then" pattern

Example test:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { Login } from './Login';

describe('Login', () => {
  it('allows the user to log in successfully', async () => {
    // Given
    render(<Login />);
    
    // When
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));
    
    // Then
    await waitFor(() => {
      expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
    });
  });
});
```

## API Development

### Adding a New Endpoint

1. Create a new route file in `app/api/` or add to an existing one
2. Define the route and its handler function
3. Add input validation using Pydantic models
4. Implement the business logic in the service layer
5. Add proper error handling
6. Write tests for the new endpoint

Example:

```python
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.photo_service import PhotoService
from app.utils.decorators import validate_json
from app.schemas.photo_schema import PhotoCreateSchema

bp = Blueprint('photos', __name__, url_prefix='/api/photos')

@bp.route('', methods=['POST'])
@jwt_required()
@validate_json(PhotoCreateSchema)
def create_photo():
    """Upload a new photo."""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        photo = PhotoService.create_photo(
            user_id=current_user_id,
            title=data['title'],
            description=data.get('description'),
            image_url=data['image_url'],
            is_public=data.get('is_public', False)
        )
        return jsonify(photo.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
```

## Frontend Development

### Adding a New Component

1. Create a new directory in `src/components/`
2. Create the component file (e.g., `NewComponent.tsx`)
3. Create a styles file if needed (e.g., `NewComponent.module.scss`)
4. Create an index file (e.g., `index.ts`) to export the component
5. Add tests in a `__tests__` directory
6. Add stories in a `__stories__` directory (if using Storybook)

### State Management

We use React Query for server state and React Context for global UI state.

Example of using React Query:

```typescript
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { getPhotos, uploadPhoto } from '../services/photoService';

function PhotoGallery() {
  const queryClient = useQueryClient();
  
  // Fetch photos
  const { data: photos, isLoading, error } = useQuery('photos', getPhotos);
  
  // Upload photo mutation
  const uploadMutation = useMutation(uploadPhoto, {
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries('photos');
    },
  });
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error loading photos</div>;
  
  return (
    <div>
      <input
        type="file"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            uploadMutation.mutate(file);
          }
        }}
      />
      
      <div className="photo-grid">
        {photos?.map((photo) => (
          <img key={photo.id} src={photo.url} alt={photo.title} />
        ))}
      </div>
    </div>
  );
}
```

## Database

### Migrations

We use Flask-Migrate for database migrations.

1. Create a new migration:
   ```bash
   flask db migrate -m "Description of changes"
   ```

2. Review the generated migration file in `migrations/versions/`

3. Apply the migration:
   ```bash
   flask db upgrade
   ```

### Seeding Data

To seed the database with test data:

```bash
flask seed all
```

## Authentication

### JWT Authentication

We use JWT (JSON Web Tokens) for authentication. The token is sent in the `Authorization` header:

```
Authorization: Bearer <token>
```

### Protected Routes

Use the `@jwt_required()` decorator to protect routes:

```python
from flask_jwt_extended import jwt_required, get_jwt_identity

@bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    return jsonify(logged_in_as=current_user_id), 200
```

## Environment Variables

### Backend

Copy `.env.example` to `.env` and update the values:

```
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/photo_portfolio
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GCS_BUCKET=your-bucket-name
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600  # 1 hour
```

### Frontend

Copy `.env.example` to `.env` and update the values:

```
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id
REACT_APP_GA_TRACKING_ID=your-ga-tracking-id
```

## Debugging

### Backend Debugging

Use the built-in Flask debugger or VS Code debugging:

1. Set breakpoints in your code
2. Start the debugger:
   ```bash
   python -m debugpy --listen 0.0.0.0:5678 -m flask run --no-debugger --no-reload
   ```
3. Attach the VS Code debugger to port 5678

### Frontend Debugging

1. Use React Developer Tools extension
2. Use the browser's developer tools
3. For Redux, use Redux DevTools

## Performance Optimization

### Backend

- Use database indexes for frequently queried fields
- Implement caching with Redis
- Use pagination for large datasets
- Optimize database queries with SQLAlchemy's `selectinload` and `joinedload`

### Frontend

- Use React.memo for pure components
- Implement code splitting with React.lazy and Suspense
- Optimize images with responsive images and WebP format
- Use React Query's built-in caching and deduplication

## Security

### Best Practices

- Always validate and sanitize user input
- Use parameterized queries to prevent SQL injection
- Implement rate limiting for authentication endpoints
- Use HTTPS in production
- Set secure HTTP headers (HSTS, CSP, etc.)
- Keep dependencies up to date
- Store secrets in environment variables or a secret manager
- Implement proper error handling to avoid information leakage

### Security Headers

We use Flask-Talisman to set security headers:

```python
from flask_talisman import Talisman

def create_app():
    app = Flask(__name__)
    Talisman(
        app,
        content_security_policy={
            'default-src': "'self'",
            'img-src': ["'self'", 'data:', 'https:'],
            'script-src': ["'self'", "'unsafe-inline'"],
            'style-src': ["'self'", "'unsafe-inline'"],
        },
        strict_transport_security=True,
        session_cookie_secure=True,
        session_cookie_http_only=True,
    )
    return app
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Run the test suite
6. Submit a pull request

### Code Review Process

1. Create a pull request
2. Request a review from at least one team member
3. Address any feedback
4. Once approved, squash and merge

### Issue Tracking

We use GitHub Issues to track bugs and feature requests. Please include:

- A clear title and description
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Screenshots if applicable
- Browser/OS version if applicable

---

This guide is a living document. Please update it as the project evolves.
