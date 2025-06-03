FROM python:3.9-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/uploads /app/static

# Copy the app
COPY simplified_app.py .

# Expose the port
EXPOSE 8080

# Set environment variables
ENV GCS_BUCKET=photoportfolio-uploads \
    SERVICE_URL=https://simplified-backend-ymcejj57ga-uc.a.run.app \
    FALLBACK_URL=https://photoportfolio-backend-er4l5fctxq-uc.a.run.app \
    PORT=8080

# Run the app with direct uvicorn command
CMD ["uvicorn", "simplified_app:app", "--host", "0.0.0.0", "--port", "8080"]
