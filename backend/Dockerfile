FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn python-multipart requests

# Create necessary directories
RUN mkdir -p /app/uploads /app/static

# Copy the app
COPY simplified_app.py .

# Expose the port
EXPOSE 8080

# Environment variables
ENV GCS_BUCKET=photoportfolio-uploads \
    SERVICE_URL=https://simplified-backend-839093975626.us-central1.run.app

# Run the app
CMD exec python simplified_app.py
