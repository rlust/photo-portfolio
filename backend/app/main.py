import os
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional

from .config import engine, Base, get_db
from .database import init_db, reset_db
from . import models, schemas
from .routes import photos, folders

# Initialize FastAPI app
app = FastAPI(
    title="Photo Portfolio API",
    description="API for managing photo portfolios",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database initialization
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing database: {e}")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if engine else "disconnected"
    }

# Reset database endpoint (for development only)
@app.post("/api/reset-db")
async def reset_database():
    if os.getenv("ENV") != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )
    reset_db()
    return {"message": "Database reset successfully"}

# Include routers
app.include_router(photos.router)
app.include_router(folders.router)

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
