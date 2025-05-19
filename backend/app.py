import os
import sys
import json
import logging
import uuid
import base64
import hashlib
import time
from datetime import datetime, timezone
import traceback
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, request, make_response, g
from flask_cors import CORS
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, DateTime, 
    func, Text, Float, Boolean, inspect, ForeignKey
)
# Alias TIMESTAMP to DateTime for compatibility
TIMESTAMP = DateTime
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector, IPTypes
import pg8000
import sqlalchemy

# Load environment variables from .env file if it exists
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# GCS Configuration
GCS_BUCKET = os.environ.get('GCS_BUCKET', 'photoportfolio-uploads')

# Database configuration
DB_CONFIG = {
    'pool_size': 5,
    'max_overflow': 10,
    'pool_timeout': 30,  # 30 seconds
    'pool_recycle': 1800,  # 30 minutes
}

def get_db_uri():
    """Generate the database connection using SQLAlchemy with Cloud SQL Auth Proxy.
    
    This function creates a SQLAlchemy engine that connects to the database through
    the Cloud SQL Auth Proxy, which should be running locally.
    """
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    
    if not all([db_user, db_password, db_name]):
        raise ValueError("Missing required database environment variables")
    
    try:
        # Create connection string for SQLAlchemy with psycopg2
        db_uri = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Create SQLAlchemy engine
        engine = sqlalchemy.create_engine(
            db_uri,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={
                'sslmode': 'disable',  # SSL is handled by the proxy
                'connect_timeout': 10,
                'client_encoding': 'utf8'
            }
        )
        
        # Test the connection with a simple query
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            if result.scalar() != 1:
                raise Exception("Unexpected result from database connection test")
        
        app.logger.info(f"Successfully connected to database: {db_name} on {db_host}:{db_port}")
        return engine
        
    except Exception as e:
        app.logger.error(f"Failed to initialize database connection: {str(e)}", exc_info=True)
        raise

def init_db():
    """Initialize database connection pool.
    
    Returns:
        SQLAlchemy engine: A configured database engine
        
    Raises:
        Exception: If database initialization fails
    """
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            app.logger.info(f"Initializing database connection (attempt {attempt + 1}/{max_retries})...")
            engine = get_db_uri()  # This now returns an engine directly
            
            # Test the connection with a simple query
            with engine.connect() as conn:
                result = conn.execute(sqlalchemy.text("SELECT 1"))
                if result.scalar() == 1:
                    app.logger.info("Database connection test successful")
                else:
                    raise Exception("Unexpected result from database connection test")
            
            return engine
            
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                app.logger.error(f"Failed to initialize database after {max_retries} attempts: {str(e)}")
                raise
                
            app.logger.warning(f"Database initialization attempt {attempt + 1} failed: {str(e)}")
            app.logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

# Initialize database engine first
try:
    engine = init_db()
    print("Database connection pool initialized successfully")
except Exception as e:
    print(f"Failed to initialize database: {e}")
    raise

# Create the declarative base with the engine
Base = declarative_base()

# Database models
class Folder(Base):
    __tablename__ = 'folders'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Define relationship to Photo
    photos = relationship("Photo", back_populates="folder", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Folder(id={self.id}, name='{self.name}')>"

class Photo(Base):
    __tablename__ = 'photos'
    
    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey('folders.id', ondelete='CASCADE'), nullable=False)
    filename = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    mimetype = Column(String(128), nullable=True)
    gcs_path = Column(String(1024), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    date_taken = Column(DateTime, nullable=True)
    date_uploaded = Column(DateTime, server_default=func.now(), nullable=True)
    is_public = Column(Boolean, default=True, nullable=True)
    location_tag = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Define relationship to Folder
    folder = relationship("Folder", back_populates="photos")
    
    def __repr__(self):
        return f"<Photo(id={self.id}, filename='{self.filename}', folder_id={self.folder_id})>"

# Create the session factory after models are defined
try:
    SessionLocal = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )
    Base.query = SessionLocal.query_property()
    print("Session factory initialized successfully")
except Exception as e:
    print(f"Failed to initialize session factory: {e}")
    raise

# Create tables if they don't exist
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables verified/created")
except Exception as e:
    print(f"Error creating database tables: {e}")
    raise

# Database session dependency
def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.teardown_appcontext
def shutdown_session(exception=None):
    """Close the database session at the end of the request."""
    if hasattr(SessionLocal, 'remove'):
        SessionLocal.remove()
    elif hasattr(SessionLocal, 'close_all'):
        SessionLocal.close_all()

@app.route('/api/__cascade_test__', methods=['GET'])
def cascade_test():
    return jsonify({
        "status": "ok",
        "message": "This is a test endpoint added by Cascade to verify deployment",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route('/')
def index():
    """Root endpoint that returns a simple welcome message."""
    # Use the datetime module correctly
    current_time = datetime.datetime.now().isoformat()
    return jsonify({
        'service': 'Photo Portfolio Backend',
        'status': 'running',
        'timestamp': current_time,
        'environment': os.environ.get('ENVIRONMENT', 'development')
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring and readiness checks.
    
    Returns:
        JSON response with service status and database connectivity.
    """
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'service': 'photo-portfolio-backend',
        'version': os.environ.get('K_REVISION', 'local'),
        'environment': os.environ.get('ENVIRONMENT', 'development'),
        'database': {
            'status': 'unknown',
            'connection': {},
            'tables': {}
        },
        'services': {
            'database': 'unknown',
            'storage': 'unknown'
        }
    }
    
    try:
        # Test database connection
        db_ok = False
        try:
            with engine.connect() as conn:
                result = conn.execute(sqlalchemy.text("SELECT 1"))
                db_ok = result.scalar() == 1
                health_data['database']['connection'] = {
                    'status': 'connected',
                    'version': conn.dialect.server_version_info
                }
                
                # Check if required tables exist
                inspector = sqlalchemy.inspect(engine)
                required_tables = ['folders', 'photos']
                tables_status = {}
                all_tables_exist = True
                
                for table in required_tables:
                    exists = inspector.has_table(table)
                    tables_status[table] = 'exists' if exists else 'missing'
                    if not exists:
                        all_tables_exist = False
                
                health_data['database']['tables'] = tables_status
                health_data['database']['status'] = 'connected' if all_tables_exist else 'degraded'
                
                if not all_tables_exist:
                    health_data['status'] = 'degraded'
                    health_data['message'] = 'Some required database tables are missing'
                
        except Exception as db_err:
            app.logger.error(f"Database health check failed: {str(db_err)}")
            health_data['database']['connection'] = {
                'status': 'error',
                'error': str(db_err)
            }
            health_data['database']['status'] = 'error'
            health_data['status'] = 'unhealthy'
        
        # Check GCS connectivity
        gcs_ok = False
        try:
            client = get_gcs_client()
            # Try to list buckets as a lightweight operation
            next(client.list_buckets(max_results=1), None)
            gcs_ok = True
            health_data['services']['storage'] = 'ok'
        except Exception as gcs_err:
            app.logger.error(f"GCS health check failed: {str(gcs_err)}")
            health_data['services']['storage'] = 'unavailable'
            health_data['status'] = 'degraded'
        
        # Update database service status
        health_data['services']['database'] = 'ok' if db_ok else 'unavailable'
        
        # Determine overall status code
        status_code = 200 if health_data['status'] == 'healthy' else 503
        
        return jsonify(health_data), status_code
        
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}", exc_info=True)
        health_data.update({
            'status': 'error',
            'error': str(e),
            'database': {
                'status': 'error',
                'connection': {
                    'status': 'error',
                    'error': str(e)
                }
            },
            'services': {
                'database': 'error',
                'storage': 'unknown'
            }
        })
        return jsonify(health_data), 500

@app.route('/api/admin/sql-dump', methods=['GET'])
def admin_sql_dump():
    """Temporary admin endpoint: returns sample rows from photos and folders tables."""
    try:
        # Get a database session
        db = next(get_db())
        
        # Query sample data using SQLAlchemy ORM
        photos = db.query(Photo).limit(20).all()
        folders = db.query(Folder).limit(20).all()
        
        # Convert SQLAlchemy objects to dictionaries
        photos_list = [{
            'id': p.id,
            'folder_id': p.folder_id,
            'filename': p.filename,
            'url': p.url,
            'mimetype': p.mimetype,
            'gcs_path': p.gcs_path,
            'width': p.width,
            'height': p.height,
            'title': p.title,
            'description': p.description,
            'date_taken': p.date_taken.isoformat() if p.date_taken else None,
            'date_uploaded': p.date_uploaded.isoformat() if p.date_uploaded else None,
            'is_public': p.is_public,
            'location_tag': p.location_tag,
            'created_at': p.created_at.isoformat() if p.created_at else None,
            'updated_at': p.updated_at.isoformat() if p.updated_at else None
        } for p in photos]
        
        folders_list = [{
            'id': f.id,
            'name': f.name,
            'created_at': f.created_at.isoformat() if f.created_at else None,
            'updated_at': f.updated_at.isoformat() if f.updated_at else None
        } for f in folders]
        
        return jsonify({"photos": photos_list, "folders": folders_list})
        
    except Exception as e:
        app.logger.error(f"Error in admin_sql_dump: {str(e)}", exc_info=True)
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/folders', methods=['GET', 'POST'])
def handle_folders():
    if request.method == 'GET':
        try:
            # Get a database session
            db = next(get_db())
            
            # Query all folders using SQLAlchemy ORM
            folders = db.query(Folder).order_by(Folder.name).all()
            
            # Convert to list of folder names
            folder_names = [folder.name for folder in folders]
            
            return jsonify(folder_names)
            
        except Exception as e:
            app.logger.error(f"Error fetching folders: {str(e)}", exc_info=True)
            # Fallback to in-memory folders if DB query fails
            return jsonify(folders)
            
    elif request.method == 'POST':
        try:
            # Get the folder data from the request
            folder_data = request.json
            if not folder_data or 'name' not in folder_data:
                return jsonify({"error": "Folder name is required"}), 400
                
            # Get a database session
            db = next(get_db())
            
            # Check if folder already exists
            existing_folder = db.query(Folder).filter(Folder.name == folder_data['name']).first()
            if existing_folder:
                return jsonify({"error": f"Folder '{folder_data['name']}' already exists"}), 409
            
            # Create new folder
            new_folder = Folder(name=folder_data['name'])
            db.add(new_folder)
            db.commit()
            
            # Return the created folder
            return jsonify({
                "id": new_folder.id,
                "name": new_folder.name,
                "created_at": new_folder.created_at.isoformat() if new_folder.created_at else None
            }), 201
            
        except Exception as e:
            db.rollback()
            app.logger.error(f"Error creating folder: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to create folder: {str(e)}"}), 500

@app.route('/api/users', methods=['GET', 'POST'])
def handle_users():
    if request.method == 'GET':
        try:
            # Get a database session
            db = next(get_db())
            
            # Query all users using SQLAlchemy ORM
            users = db.query(User).order_by(User.username).all()
            
            # Convert to list of usernames
            user_list = [{
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat() if user.created_at else None
            } for user in users]
            
            return jsonify(user_list)
            
        except Exception as e:
            app.logger.error(f"Error fetching users: {str(e)}", exc_info=True)
            # Fallback to in-memory users if DB query fails
            return jsonify(users)
            
    elif request.method == 'POST':
        try:
            # Get the user data from the request
            user_data = request.json
            required_fields = ['username', 'email', 'password']
            
            # Validate required fields
            if not all(field in user_data for field in required_fields):
                return jsonify({"error": "Missing required fields. Required: username, email, password"}), 400
            
            # Get a database session
            db = next(get_db())
            
            # Check if username or email already exists
            existing_user = db.query(User).filter(
                (User.username == user_data['username']) | 
                (User.email == user_data['email'])
            ).first()
            
            if existing_user:
                conflict_field = 'username' if existing_user.username == user_data['username'] else 'email'
                return jsonify({"error": f"User with this {conflict_field} already exists"}), 409
            
            # Hash the password (in a real app, use a proper password hashing library)
            # For production, use: from passlib.context import CryptContext
            # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            # hashed_password = pwd_context.hash(user_data['password'])
            hashed_password = user_data['password']  # Insecure - replace with proper hashing
            
            # Create new user
            new_user = User(
                username=user_data['username'],
                email=user_data['email'],
                hashed_password=hashed_password,
                is_active=user_data.get('is_active', True),
                is_admin=user_data.get('is_admin', False)
            )
            
            db.add(new_user)
            db.commit()
            
            # Return the created user (without the hashed password)
            return jsonify({
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "is_active": new_user.is_active,
                "is_admin": new_user.is_admin,
                "created_at": new_user.created_at.isoformat() if new_user.created_at else None
            }), 201
            
        except Exception as e:
            db.rollback()
            app.logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to create user: {str(e)}"}), 500

@app.route('/api/photos', methods=['GET', 'POST'])
def handle_photos():
    print("\n=== Starting handle_photos ===")
    print(f"Request method: {request.method}")
    
    # Debug: Print request data for POST
    if request.method == 'POST':
        print(f"Request JSON: {request.json}")
        
    # Debug: Print Photo model attributes
    print("\n=== Photo Model Attributes ===")
    print(f"Photo.__dict__: {dir(Photo)}")
    print(f"Photo.__table__.columns: {[c.name for c in Photo.__table__.columns]}")
    print("==============================\n")
    
    db = SessionLocal()
    try:
        if request.method == 'GET':
            print("Handling GET request")
            photos = db.query(Photo).all()
            print(f"Found {len(photos)} photos in database")
            return jsonify([{
                'id': p.id,
                'folder_id': p.folder_id,
                'filename': p.filename,
                'url': p.url,
                'mimetype': p.mimetype,
                'width': p.width,
                'height': p.height,
                'title': p.title,
                'description': p.description,
                'date_taken': p.date_taken.isoformat() if p.date_taken else None,
                'date_uploaded': p.date_uploaded.isoformat() if p.date_uploaded else None,
                'is_public': p.is_public,
                'location_tag': p.location_tag
            } for p in photos])
            
        elif request.method == 'POST':
            print("Handling POST request")
            photo_data = request.json
            print(f"Received photo data: {photo_data}")
            
            # Validate required fields
            required_fields = ['folder_id', 'filename', 'url']
            missing_fields = [field for field in required_fields if field not in photo_data]
            
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                print(f"Validation error: {error_msg}")
                return jsonify({"error": error_msg}), 400
            
            print(f"Checking for existing photo with folder_id={photo_data['folder_id']} and filename={photo_data['filename']}")
            
            # Check if folder exists
            folder = db.query(Folder).filter(Folder.id == photo_data['folder_id']).first()
            if not folder:
                error_msg = f"Folder with ID {photo_data['folder_id']} does not exist"
                print(error_msg)
                return jsonify({"error": error_msg}), 404
            
            # Check if photo already exists with the same filename in the same folder
            try:
                existing_photo = db.query(Photo).filter(
                    Photo.folder_id == photo_data['folder_id'],
                    Photo.filename == photo_data['filename']
                ).first()
                
                if existing_photo:
                    error_msg = f"Photo with filename '{photo_data['filename']}' already exists in this folder"
                    print(error_msg)
                    return jsonify({"error": error_msg}), 409
                    
            except Exception as e:
                print(f"Error checking for existing photo: {e}")
                print(f"Error type: {type(e).__name__}")
                if hasattr(e, '__dict__'):
                    print(f"Error details: {e.__dict__}")
                raise
            
            print("Creating new photo...")
            
            try:
                # Create new photo with explicit attribute setting
                try:
                    print("\n=== Creating new Photo instance ===")
                    new_photo = Photo()
                    print(f"Created new Photo instance: {new_photo}")
                    print(f"New photo attributes: {dir(new_photo)}")
                except Exception as e:
                    print(f"Error creating Photo instance: {e}")
                    print(f"Error type: {type(e).__name__}")
                    if hasattr(e, '__dict__'):
                        print(f"Error details: {e.__dict__}")
                    raise
                
                # Set required fields
                try:
                    print("\n=== Setting required fields ===")
                    print(f"Setting folder_id: {photo_data['folder_id']} (type: {type(photo_data['folder_id'])})")
                    
                    # Convert folder_id to integer if it's a string
                    folder_id = int(photo_data['folder_id']) if isinstance(photo_data['folder_id'], str) else photo_data['folder_id']
                    
                    # Set attributes using setattr to avoid attribute access issues
                    setattr(new_photo, 'folder_id', folder_id)
                    setattr(new_photo, 'filename', photo_data['filename'])
                    setattr(new_photo, 'url', photo_data['url'])
                    
                    print("Successfully set required fields")
                    print(f"New photo attributes after setting: {new_photo.__dict__}")
                except Exception as e:
                    print(f"Error setting required fields: {e}")
                    print(f"Error type: {type(e).__name__}")
                    if hasattr(e, '__dict__'):
                        print(f"Error details: {e.__dict__}")
                    print(f"Available attributes: {dir(new_photo)}")
                    raise
                
                # Set optional fields
                if 'mimetype' in photo_data:
                    new_photo.mimetype = photo_data['mimetype']
                if 'gcs_path' in photo_data:
                    new_photo.gcs_path = photo_data['gcs_path']
                if 'width' in photo_data:
                    new_photo.width = int(photo_data['width']) if photo_data['width'] is not None else None
                if 'height' in photo_data:
                    new_photo.height = int(photo_data['height']) if photo_data['height'] is not None else None
                if 'title' in photo_data:
                    new_photo.title = photo_data['title']
                if 'description' in photo_data:
                    new_photo.description = photo_data['description']
                if 'location_tag' in photo_data:
                    new_photo.location_tag = photo_data['location_tag']
                if 'is_public' in photo_data:
                    new_photo.is_public = bool(photo_data['is_public'])
                else:
                    new_photo.is_public = True
                
                print("Set optional fields")
                
                # Set date_taken if provided, otherwise use current time
                if 'date_taken' in photo_data and photo_data['date_taken']:
                    try:
                        new_photo.date_taken = datetime.datetime.fromisoformat(photo_data['date_taken'])
                        print(f"Set date_taken to {new_photo.date_taken}")
                    except (ValueError, TypeError) as e:
                        print(f"Warning: Invalid date format for date_taken: {e}")
                
                print("Adding photo to session...")
                db.add(new_photo)
                print("Committing transaction...")
                db.commit()
                print(f"Successfully created photo with ID: {new_photo.id}")
                
                # Refresh to get database-generated values
                db.refresh(new_photo)
                
                # Return the created photo
                response_data = {
                    'id': new_photo.id,
                    'folder_id': new_photo.folder_id,
                    'filename': new_photo.filename,
                    'url': new_photo.url,
                    'mimetype': new_photo.mimetype,
                    'width': new_photo.width,
                    'height': new_photo.height,
                    'title': new_photo.title,
                    'description': new_photo.description,
                    'date_taken': new_photo.date_taken.isoformat() if new_photo.date_taken else None,
                    'date_uploaded': new_photo.date_uploaded.isoformat() if new_photo.date_uploaded else None,
                    'is_public': new_photo.is_public,
                    'location_tag': new_photo.location_tag
                }
                
                print(f"Returning response: {response_data}")
                return jsonify(response_data), 201
                
            except Exception as create_error:
                db.rollback()
                print(f"Error creating photo: {str(create_error)}")
                print(f"Error type: {type(create_error).__name__}")
                if hasattr(create_error, '__dict__'):
                    print(f"Error details: {create_error.__dict__}")
                raise  # Re-raise the error to be caught by the outer try/except
                
    except Exception as e:
        db.rollback()
        error_type = type(e).__name__
        error_details = str(e)
        print(f"Error in handle_photos: {error_type} - {error_details}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            "error": f"Failed to process request",
            "type": error_type,
            "details": error_details
        }), 500
    finally:
        print("Closing database session")
        db.close()
        print("=== End of handle_photos ===\n")

# --- Database Helper Functions ---
def add_folder_to_db(folder_name):
    """
    Add a folder to the database if it doesn't already exist.
    
    Args:
        folder_name (str): Name of the folder to add
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Get a database session
        db = next(get_db())
        
        # Check if folder already exists
        existing_folder = db.query(Folder).filter(Folder.name == folder_name).first()
        
        if existing_folder:
            return True, f"Folder '{folder_name}' already exists"
        
        # Create new folder
        new_folder = Folder(name=folder_name)
        db.add(new_folder)
        db.commit()
        
        return True, f"Added folder '{folder_name}' with ID {new_folder.id}"
        
    except Exception as e:
        db.rollback()
        app.logger.error(f"Error in add_folder_to_db: {str(e)}", exc_info=True)
        return False, f"Error adding folder: {str(e)}"

def add_photo_to_db(folder_name, filename, url, mimetype=None, gcs_path=None, **kwargs):
    """
    Add a photo to the database if it doesn't already exist.
    
    Args:
        folder_name (str): Name of the folder containing the photo
        filename (str): Name of the photo file
        url (str): Public URL of the photo
        mimetype (str, optional): MIME type of the photo
        gcs_path (str, optional): Path to the photo in Google Cloud Storage
        **kwargs: Additional photo metadata (width, height, title, description, etc.)
        
    Returns:
        tuple: (success: bool, message: str, photo_id: int or None)
    """
    try:
        # Get a database session
        db = next(get_db())
        
        # Get folder
        folder = db.query(Folder).filter(Folder.name == folder_name).first()
        if not folder:
            return False, f"Folder '{folder_name}' not found", None
        
        # Check if photo already exists
        existing_photo = db.query(Photo).filter(
            Photo.folder_id == folder.id,
            Photo.filename == filename
        ).first()
        
        if existing_photo:
            return True, f"Photo '{filename}' already exists in folder '{folder_name}'", existing_photo.id
        
        # Create new photo
        new_photo = Photo(
            folder_id=folder.id,
            filename=filename,
            url=url,
            mimetype=mimetype,
            gcs_path=gcs_path,
            **{k: v for k, v in kwargs.items() if k in [
                'width', 'height', 'title', 'description', 
                'date_taken', 'is_public', 'location_tag'
            ]}
        )
        
        db.add(new_photo)
        db.commit()
        
        return True, f"Added photo '{filename}' to folder '{folder_name}'", new_photo.id
        
        return {'status': 'created', 'photo_id': new_photo.id}
    except Exception as e:
        db.session.rollback()
        import traceback
        error_msg = f"[PHOTO-PORTFOLIO] [add_photo_to_db] ERROR: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise

# --- GCS Client Initialization ---
def get_gcs_client():
    """Initialize and return a Google Cloud Storage client using Workload Identity.
    
    This function will automatically use the credentials provided by the environment,
    which in Cloud Run will be the service account's Workload Identity.
    """
    try:
        # This will automatically use the service account attached to the Cloud Run service
        from google.cloud import storage
        
        # Create client with default credentials (Workload Identity in production)
        # No need for explicit credentials file with Workload Identity
        client = storage.Client()
        
        # Verify client can access the bucket (will raise an exception if not)
        # This helps catch authentication/authorization issues early
        try:
            bucket = client.get_bucket(GCS_BUCKET)
            app.logger.debug(f"Successfully connected to GCS bucket: {bucket.name}")
        except Exception as e:
            app.logger.error(f"Failed to access GCS bucket {GCS_BUCKET}: {str(e)}")
            raise
            
        return client
        
    except Exception as e:
        app.logger.error(f"Failed to initialize GCS client: {str(e)}")
        raise  # Re-raise the exception to fail fast in case of auth issues

# --- GCS Reindexing Endpoint ---
@app.route('/api/reindex-gcs', methods=['POST'])
def reindex_gcs():
    """
    Reindex all photos in the GCS bucket and update the database.
    
    This endpoint scans the configured GCS bucket, identifies all folders and photos,
    and updates the database to reflect the current state of the storage.
    """
    app.logger.info("Starting GCS reindexing process")
    
    try:
        # Get database session
        db = next(get_db())
        
        # Get GCS client and bucket
        storage_client = get_gcs_client()
        bucket = storage_client.bucket(GCS_BUCKET)
        
        # Track statistics
        stats = {
            'folders_processed': 0,
            'folders_added': 0,
            'photos_processed': 0,
            'photos_added': 0,
            'photos_skipped': 0,
            'errors': []
        }
        
        # Process each folder (prefix) in the bucket
        folders = set()
        blobs = storage_client.list_blobs(GCS_BUCKET, prefix='folders/')
        
        # First pass: identify all folders
        app.logger.info("Scanning GCS bucket for folders...")
        for blob in blobs:
            # Extract folder name (second part of the path after 'folders/')
            parts = blob.name.split('/')
            if len(parts) >= 2 and parts[0] == 'folders' and parts[1]:
                folder_name = parts[1]
                folders.add(folder_name)
        
        app.logger.info(f"Found {len(folders)} folders in bucket {GCS_BUCKET}")
        
        # Process each folder
        for folder_name in sorted(folders):
            try:
                app.logger.info(f"Processing folder: {folder_name}")
                
                # Add folder to database if it doesn't exist
                success, message = add_folder_to_db(folder_name)
                if success:
                    if 'already exists' not in message:
                        stats['folders_added'] += 1
                        app.logger.info(f"Added folder: {message}")
                    else:
                        app.logger.debug(f"Folder '{folder_name}': {message}")
                    stats['folders_processed'] += 1
                else:
                    error_msg = f"Error processing folder '{folder_name}': {message}"
                    app.logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    continue
                
                # Get all blobs in this folder (non-recursive)
                folder_prefix = f"folders/{folder_name}/"
                folder_blobs = storage_client.list_blobs(GCS_BUCKET, prefix=folder_prefix)
                
                # Process each photo in the folder
                for blob in folder_blobs:
                    try:
                        # Skip if this is a folder marker or hidden file
                        if blob.name.endswith('/') or blob.name.startswith('.'):
                            continue
                            
                        stats['photos_processed'] += 1
                        
                        # Generate public URL
                        url = f"https://storage.googleapis.com/{GCS_BUCKET}/{blob.name}"
                        
                        # Extract filename and metadata
                        filename = blob.name.split('/')[-1]
                        
                        # Get image dimensions if it's an image
                        width = height = None
                        if blob.content_type and blob.content_type.startswith('image/'):
                            try:
                                # Download a small portion of the image to get dimensions
                                with io.BytesIO() as img_data:
                                    blob.download_to_file(img_data)
                                    img_data.seek(0)
                                    with Image.open(img_data) as img:
                                        width, height = img.size
                            except Exception as img_error:
                                app.logger.warning(f"Could not get dimensions for {blob.name}: {str(img_error)}")
                        
                        # Add photo to database
                        success, message, _ = add_photo_to_db(
                            folder_name=folder_name,
                            filename=filename,
                            url=url,
                            mimetype=blob.content_type,
                            gcs_path=blob.name,
                            width=width,
                            height=height,
                            title=filename.rsplit('.', 1)[0].replace('_', ' ').title(),
                            date_taken=blob.time_created or datetime.datetime.utcnow()
                        )
                        
                        if success:
                            if 'already exists' in message:
                                stats['photos_skipped'] += 1
                                app.logger.debug(f"Skipped existing photo: {filename}")
                            else:
                                stats['photos_added'] += 1
                                app.logger.info(f"Added photo: {message}")
                        else:
                            error_msg = f"Error adding photo '{blob.name}': {message}"
                            app.logger.error(error_msg)
                            stats['errors'].append(error_msg)
                        
                    except Exception as e:
                        error_msg = f"Error processing photo '{blob.name}': {str(e)}"
                        app.logger.error(error_msg, exc_info=True)
                        stats['errors'].append(error_msg)
                        continue
                        
            except Exception as e:
                error_msg = f"Error processing folder '{folder_name}': {str(e)}"
                app.logger.error(error_msg, exc_info=True)
                stats['errors'].append(error_msg)
                continue
        
        # Clean up any orphaned records (photos in DB but not in storage)
        try:
            app.logger.info("Checking for orphaned photos in database...")
            # Get all photos from DB for the folders we just processed
            db_photos = db.query(Photo).filter(Photo.folder_id.in_(
                db.query(Folder.id).filter(Folder.name.in_(folders))
            )).all()
            
            db_photo_paths = {photo.gcs_path for photo in db_photos if photo.gcs_path}
            
            # Get all blobs from storage
            storage_blobs = list(storage_client.list_blobs(GCS_BUCKET, prefix='folders/'))
            storage_paths = {blob.name for blob in storage_blobs if not blob.name.endswith('/')}
            
            # Find orphaned photos (in DB but not in storage)
            orphaned_photos = db_photo_paths - storage_paths
            
            if orphaned_photos:
                app.logger.info(f"Found {len(orphaned_photos)} orphaned photos to clean up")
                deleted_count = db.query(Photo).filter(Photo.gcs_path.in_(orphaned_photos)).delete()
                db.commit()
                stats['orphaned_photos_removed'] = deleted_count
                app.logger.info(f"Removed {deleted_count} orphaned photos from database")
                
        except Exception as e:
            error_msg = f"Error cleaning up orphaned photos: {str(e)}"
            app.logger.error(error_msg, exc_info=True)
            stats['errors'].append(error_msg)
        
        # Log completion
        app.logger.info(f"GCS reindexing completed. Stats: {json.dumps(stats, indent=2)}")
        
        # Return success response with statistics
        return jsonify({
            'status': 'success',
            'message': 'GCS reindexing completed successfully',
            'stats': stats
        }), 200
        
    except Exception as e:
        error_msg = f"Error during GCS reindexing: {str(e)}"
        app.logger.error(error_msg, exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to reindex GCS bucket',
            'error': error_msg,
            'details': str(e)
        }), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


from werkzeug.utils import secure_filename
from google.cloud import storage
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker, declarative_base
import threading
import datetime
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import os
import sys
import json
import logging
import uuid
import base64
import hashlib
import time
import datetime
import traceback
from datetime import datetime, timezone
from functools import wraps

# Print DB path on startup
DB_PATH = os.environ.get('DB_PATH', 'metadata.db')
print(f"[PHOTO-PORTFOLIO] Using DB file: {os.path.abspath(DB_PATH)}")
logging.info(f"Using DB file: {os.path.abspath(DB_PATH)}")

from PIL import Image
import exifread
from geopy.geocoders import Nominatim
from google.cloud import vision
import io

# --- Location Tag Utilities ---
def extract_gps_from_exif(image_path):
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        gps_lat = tags.get('GPS GPSLatitude')
        gps_lat_ref = tags.get('GPS GPSLatitudeRef')
        gps_lon = tags.get('GPS GPSLongitude')
        gps_lon_ref = tags.get('GPS GPSLongitudeRef')
        if gps_lat and gps_lat_ref and gps_lon and gps_lon_ref:
            def _dms_to_deg(dms, ref):
                d = float(dms.values[0].num) / float(dms.values[0].den)
                m = float(dms.values[1].num) / float(dms.values[1].den)
                s = float(dms.values[2].num) / float(dms.values[2].den)
                deg = d + m/60.0 + s/3600.0
                if ref.values[0] in ['S', 'W']:
                    deg = -deg
                return deg
            lat = _dms_to_deg(gps_lat, gps_lat_ref)
            lon = _dms_to_deg(gps_lon, gps_lon_ref)
            return lat, lon
    except Exception:
        pass
    return None

def reverse_geocode(lat, lon):
    try:
        geolocator = Nominatim(user_agent="photoportfolio")
        location = geolocator.reverse((lat, lon), language='en', timeout=10)
        return location.address if location else None
    except Exception:
        return None

def google_vision_landmark(image_bytes):
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        response = client.landmark_detection(image=image)
        landmarks = response.landmark_annotations
        if landmarks:
            return landmarks[0].description
    except Exception:
        pass
    return None

@app.route('/api/annotate-locations', methods=['POST'])
def annotate_locations():
    print(f"[PHOTO-PORTFOLIO] [annotate_locations] Using DB file: {os.path.abspath(DB_PATH)}")
    logging.info(f"[annotate_locations] Using DB file: {os.path.abspath(DB_PATH)}")
    """
    Batch annotate photos in the DB with location_tag using EXIF GPS (if available),
    else Google Vision landmark detection. Processes only a batch per call.
    Query params:
      - batch_size (default 10)
      - offset (default 0)
    Returns: progress info and how many annotated in this batch.
    """
    import tempfile, requests
    batch_size = int(request.args.get('batch_size', 10))
    offset = int(request.args.get('offset', 0))
    updated = 0
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Count total untagged
        c.execute('SELECT COUNT(*) FROM photos WHERE location_tag IS NULL OR location_tag = "" OR location_tag = "null"')
        total_untagged = c.fetchone()[0]
        # Get batch
        c.execute('SELECT id, url FROM photos WHERE location_tag IS NULL OR location_tag = "" OR location_tag = "null" LIMIT ? OFFSET ?', (batch_size, offset))
        photos = c.fetchall()
        for photo_id, url in photos:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                # 1. Try EXIF GPS
                gps = extract_gps_from_exif(tmp_path)
                tag = None
                if gps:
                    lat, lon = gps
                    tag = reverse_geocode(lat, lon)
                # 2. If no GPS, try Vision API
                if not tag:
                    tag = google_vision_landmark(resp.content)
                # 3. If found, update DB
                if tag:
                    c.execute('UPDATE photos SET location_tag=? WHERE id=?', (tag, photo_id))
                    updated += 1
                os.remove(tmp_path)
            except Exception:
                continue
        # Count remaining after this batch
        c.execute('SELECT COUNT(*) FROM photos WHERE location_tag IS NULL OR location_tag = ""')
        remaining = c.fetchone()[0]
        conn.commit()
        conn.close()
    return jsonify({
        'status': 'ok',
        'batch_size': batch_size,
        'offset': offset,
        'updated_this_batch': updated,
        'remaining_untagged': remaining,
        'total_untagged': total_untagged
    })

# --- Direct-to-GCS Upload Endpoints ---
from flask import make_response

@app.route('/api/get-signed-url', methods=['POST'])
def get_signed_url():
    try:
        data = request.get_json()
        if not data or 'filename' not in data or 'mimetype' not in data:
            return jsonify({'error': 'Missing required fields: filename and mimetype are required'}), 400
        
        # Generate a unique filename to avoid collisions
        import uuid
        filename = str(uuid.uuid4()) + '_' + data['filename'].replace(' ', '_')
        folder = data.get('folder', 'uploads')
        
        # Create the blob path
        blob_path = f"{folder}/{filename}"
        
        # Generate the signed URL
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        
        # Set content type and metadata
        content_type = data['mimetype']
        metadata = data.get('metadata', {})
        
        # Generate signed URL that's valid for 30 minutes
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=30),
            method="PUT",
            content_type=content_type,
            headers={"x-goog-meta-" + k: str(v) for k, v in metadata.items()}
        )
        
        return jsonify({
            'signed_url': signed_url,
            'public_url': f"https://storage.googleapis.com/{GCS_BUCKET}/{blob_path}",
            'filename': filename,
            'path': blob_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
_db_lock = threading.Lock()

import os
from dotenv import load_dotenv

# Load DB credentials from file
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), 'db_credentials.txt')
DB_USER = DB_PASSWORD = DB_NAME = DB_INSTANCE = DB_REGION = None
if os.path.exists(CREDENTIALS_PATH):
    with open(CREDENTIALS_PATH) as f:
        for line in f:
            if line.startswith('DB_USER:'):
                DB_USER = line.split(':',1)[1].strip()
            elif line.startswith('DB_PASSWORD:'):
                DB_PASSWORD = line.split(':',1)[1].strip()
            elif line.startswith('DB_NAME:'):
                DB_NAME = line.split(':',1)[1].strip()
            elif line.startswith('DB_INSTANCE:'):
                DB_INSTANCE = line.split(':',1)[1].strip()
            elif line.startswith('DB_REGION:'):
                DB_REGION = line.split(':',1)[1].strip()

# Cloud SQL PostgreSQL connection string
# Use Unix socket for production (Cloud Run), TCP for local development
import platform
import sys

IS_PROD = any(os.environ.get(k) for k in ["GAE_ENV", "K_SERVICE", "CLOUD_RUN"])
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")

# Diagnostic logging for DB env vars
required_vars = {
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "DB_NAME": DB_NAME,
    "DB_INSTANCE": DB_INSTANCE,
    "DB_REGION": DB_REGION,
}
missing = [k for k, v in required_vars.items() if not v]
if missing:
    print(f"[ERROR] Missing required DB environment variables: {missing}", file=sys.stderr)
    for k, v in required_vars.items():
        print(f"{k}={v}", file=sys.stderr)
    sys.exit(1)
else:
    print("[INFO] All DB env vars set:")
    for k, v in required_vars.items():
        print(f"{k}={v}")

# Use the get_db_uri() function to ensure consistent database connection settings
engine = get_db_uri()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DOCUMENTATION:
# - For local dev, run the Cloud SQL Auth Proxy:
#   ./cloud-sql-proxy --address 127.0.0.1 --port 5432 photoportfolio-db:us-central1:photoportfolio-db
#   or use DB_HOST/DB_PORT in your environment.
# - For Cloud Run, no proxy needed (uses socket).

class Folder(Base):
    __tablename__ = 'folders'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)

class Photo(Base):
    __tablename__ = 'photos'
    id = Column(Integer, primary_key=True, index=True)
    folder = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    mimetype = Column(String(128))
    gcs_path = Column(String(1024))
    uploaded_at = Column(DateTime, server_default=func.now())
    location_tag = Column(String(255))

# Create tables if not exist (safe for production)
Base.metadata.create_all(bind=engine)

def init_db():
    # No-op: DB schema is managed by SQLAlchemy/PostgreSQL
    print("[PHOTO-PORTFOLIO] [init_db] (noop) DB schema managed by SQLAlchemy/PostgreSQL.")
    logging.info("[init_db] (noop) DB schema managed by SQLAlchemy/PostgreSQL.")

init_db()

def get_gcs_client():
    return storage.Client()

def ensure_bucket_exists():
    client = get_gcs_client()
    bucket = client.bucket(GCS_BUCKET)
    if not bucket.exists():
        bucket = client.create_bucket(GCS_BUCKET, location="us")
        bucket.iam_configuration.uniform_bucket_level_access_enabled = True
        bucket.patch()
        # Make bucket public
        bucket.make_public(future=True)
    return bucket

def upload_to_gcs(file, folder):
    client = get_gcs_client()
    bucket = ensure_bucket_exists()
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    blob_path = f"folders/{folder}/{unique_name}"
    blob = bucket.blob(blob_path)
    blob.upload_from_file(file, content_type=file.mimetype)
    # Do not call blob.make_public(); rely on bucket-level IAM for public access
    return {
        'name': filename,
        'url': f'https://storage.googleapis.com/{bucket.name}/{blob_path}',
        'mimetype': file.mimetype,
        'gcs_path': blob_path
    }

def add_folder_to_db(folder):
    with _db_lock:
        db = SessionLocal()
        if not db.query(Folder).filter_by(name=folder).first():
            db.add(Folder(name=folder))
            db.commit()
        db.close()

def add_photo_to_db(folder, name, url, mimetype, gcs_path, location_tag=None):
    with _db_lock:
        db = SessionLocal()
        photo = Photo(folder=folder, name=name, url=url, mimetype=mimetype, gcs_path=gcs_path, location_tag=location_tag)
        db.add(photo)
        db.commit()
        db.close()

def get_all_folders():
    with _db_lock:
        db = SessionLocal()
        folders = [f.name for f in db.query(Folder).all()]
        db.close()
        return folders

def get_photos_by_folder():
    with _db_lock:
        db = SessionLocal()
        photos = db.query(Photo).all()
        db.close()
        folder_dict = {}
        for photo in photos:
            folder_dict.setdefault(photo.folder, []).append({
                'name': photo.name,
                'url': photo.url,
                'mimetype': photo.mimetype,
                'location_tag': photo.location_tag
            })
        return folder_dict

def delete_photo_from_db(folder, name):
    with _db_lock:
        db = SessionLocal()
        photo = db.query(Photo).filter_by(folder=folder, name=name).first()
        if photo:
            gcs_path = photo.gcs_path
            db.delete(photo)
            db.commit()
            db.close()
            # Delete from GCS
            client = get_gcs_client()
            bucket = client.bucket(GCS_BUCKET)
            blob = bucket.blob(gcs_path)
            blob.delete()
            return True
        db.close()
        return False

def delete_folder_from_db(folder):
    with _db_lock:
        db = SessionLocal()
        photos = db.query(Photo).filter_by(folder=folder).all()
        gcs_paths = [p.gcs_path for p in photos]
        for photo in photos:
            db.delete(photo)
        db.query(Folder).filter_by(name=folder).delete()
        db.commit()
        db.close()
        # Delete all blobs in GCS for this folder
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        for gcs_path in gcs_paths:
            blob = bucket.blob(gcs_path)
            blob.delete()
        return True

from flask import make_response

@app.errorhandler(413)
def handle_413(e):
    response = make_response(jsonify({'error': 'Request too large. Each batch must be under 32MB.'}), 413)
    response.headers['Access-Control-Allow-Origin'] = get_cors_origin()
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return response

@app.route('/api/upload', methods=['POST'])
def upload_photos():
    import traceback
    folder = request.form.get('folder')
    files = request.files.getlist('images')
    if not folder or not files:
        resp = make_response(jsonify({'error': 'Folder name and images are required.'}), 400)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    folder = secure_filename(folder)
    add_folder_to_db(folder)
    uploaded = []
    for file in files:
        try:
            file.stream.seek(0)
            photo_info = upload_to_gcs(file, folder)
            add_photo_to_db(folder, photo_info['name'], photo_info['url'], photo_info['mimetype'], photo_info['gcs_path'])
            uploaded.append({'name': photo_info['name'], 'url': photo_info['url'], 'mimetype': photo_info['mimetype']})
        except Exception as e:
            print(f"[UPLOAD ERROR] {e}\n{traceback.format_exc()}")
            # Continue uploading other files, but log error
    resp = make_response(jsonify({'folder': folder, 'uploaded': uploaded, 'folders': get_all_folders()}), 201)
    resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp

@app.route('/api/folders', methods=['GET', 'OPTIONS'])
def get_folders():
    if request.method == 'OPTIONS':
        # Preflight CORS
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    try:
        resp = make_response(jsonify(get_photos_by_folder()))
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    except Exception as e:
        resp = make_response(jsonify({'error': str(e)}), 500)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp

@app.route('/api/photos/search', methods=['GET'])
def search_photos():
    name = request.args.get('name', '').strip()
    folder = request.args.get('folder', '').strip()
    mimetype = request.args.get('mimetype', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    query = "SELECT folder, name, url, mimetype, uploaded_at FROM photos WHERE 1=1"
    params = []
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if folder:
        query += " AND folder=?"
        params.append(folder)
    if mimetype:
        query += " AND mimetype LIKE ?"
        params.append(f"%{mimetype}%")
    if date_from:
        query += " AND uploaded_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND uploaded_at <= ?"
        params.append(date_to)
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
    results = [
        {'folder': f, 'name': n, 'url': u, 'mimetype': m, 'uploaded_at': d}
        for f, n, u, m, d in rows
    ]
    return jsonify(results)

@app.route('/api/folders/search', methods=['GET'])
def search_folders():
    name = request.args.get('name', '').strip()
    with _db_lock:
        db = SessionLocal()
        q = db.query(Folder)
        if name:
            q = q.filter(Folder.name.ilike(f"%{name}%"))
        results = [f.name for f in q.all()]
        db.close()
    return jsonify(results)

@app.route('/api/folder/<folder>', methods=['DELETE'])
def delete_folder(folder):
    folder = secure_filename(folder)
    success = delete_folder_from_db(folder)
    if success:
        return jsonify({'message': f'Folder {folder} deleted.'}), 200
    else:
        return jsonify({'error': 'Folder not found'}), 404

@app.route('/api/folder/<folder>/<name>', methods=['DELETE'])
def delete_photo(folder, name):
    folder = secure_filename(folder)
    name = secure_filename(name)
    success = delete_photo_from_db(folder, name)
    if success:
        return jsonify({'message': f'Photo {name} deleted from folder {folder}.'}), 200
    else:
        return jsonify({'error': 'Photo not found'}), 404

# --- Direct-to-GCS Upload Endpoints ---
# Using the route at /api/get-signed-url
# Removed duplicate route at /api/signed-url

@app.route('/api/register-upload', methods=['POST'])
def register_upload():
    data = request.get_json()
    filename = data.get('filename')
    content_type = data.get('contentType')
    folder = secure_filename(data.get('folder', 'uploads'))
    public_url = data.get('publicUrl')
    gcs_path = data.get('gcsPath')
    if not filename or not content_type or not folder or not public_url:
        resp = make_response(jsonify({'error': 'filename, contentType, folder, and publicUrl are required'}), 400)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    add_folder_to_db(folder)
    add_photo_to_db(folder, filename, public_url, content_type, gcs_path or '')
    resp = make_response(jsonify({'ok': True}), 200)
    resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp

import os
# --- AI-powered Semantic Search Endpoint ---
# Model is loaded at module level to avoid reloading on every request
_semantic_model = SentenceTransformer('all-MiniLM-L6-v2')

@app.route('/api/photos/semantic-search', methods=['GET'])
def semantic_search_photos():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Missing query'}), 400
    # Fetch all photo metadata from DB
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT folder, name, url, mimetype, uploaded_at FROM photos')
        rows = c.fetchall()
        conn.close()
    if not rows:
        return jsonify([])
    # Prepare texts for embedding
    photo_texts = [f"{name} {folder} {mimetype}" for folder, name, url, mimetype, uploaded_at in rows]
    photo_embeddings = _semantic_model.encode(photo_texts)
    query_embedding = _semantic_model.encode([query])[0]
    # Compute cosine similarity
    similarities = np.dot(photo_embeddings, query_embedding) / (
        np.linalg.norm(photo_embeddings, axis=1) * np.linalg.norm(query_embedding) + 1e-8
    )
    top_indices = np.argsort(similarities)[::-1][:10]  # Top 10
    results = [
        {
            'folder': rows[i][0],
            'name': rows[i][1],
            'url': rows[i][2],
            'mimetype': rows[i][3],
            'uploaded_at': rows[i][4],
            'score': float(similarities[i])
        }
        for i in top_indices
    ]
    return jsonify(results)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
