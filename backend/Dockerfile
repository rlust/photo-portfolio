# ===================================
# Build stage
# ===================================
FROM python:3.11-slim-bookworm as builder

# Set environment variables
ENV \
    # Python settings
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    # Set Python path
    PYTHONPATH="/app:$PYTHONPATH" \
    # Set build arguments
    BUILD_DEPS="wget gnupg2 curl git" \
    RUNTIME_DEPS="netcat-openbsd" \
    BUILD_ESSENTIALS="gcc python3-dev build-essential libpq-dev"

# Install system dependencies
RUN set -ex \
    && apt-get update \
    && apt-get install -y --no-install-recommends $BUILD_DEPS $RUNTIME_DEPS $BUILD_ESSENTIALS \
    && rm -rf /var/lib/apt/lists/*

# Install Cloud SQL Proxy
ENV CLOUD_SQL_PROXY_VERSION=v2.8.0
RUN set -ex \
    && wget -q https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/${CLOUD_SQL_PROXY_VERSION}/cloud-sql-proxy.linux.amd64 \
        -O /usr/local/bin/cloud-sql-proxy \
    && chmod +x /usr/local/bin/cloud-sql-proxy \
    && cloud-sql-proxy --version

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies with pip-tools for better dependency resolution
RUN set -ex \
    && pip install --upgrade pip setuptools wheel pip-tools \
    && pip-sync requirements.txt \
    && pip install --no-cache-dir gunicorn uvicorn email-validator

# Install psycopg2 for PostgreSQL connection
RUN pip install --no-cache-dir \
    'psycopg2-binary>=2.9.0' \
    'sqlalchemy[asyncio]>=2.0.0,<3.0.0'

# Install PyTorch with CPU support
RUN pip install --no-cache-dir \
    torch==2.0.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install transformers and related packages with specific versions
RUN pip install --no-cache-dir \
    'transformers==4.30.0' \
    'nltk==3.8.1' \
    && pip install --no-cache-dir --no-deps 'sentence-transformers==2.2.2'

# Download NLTK data and model in the builder stage
RUN set -ex \
    && mkdir -p /root/nltk_data/tokenizers \
    && python -c "import nltk; nltk.download('punkt', download_dir='/root/nltk_data')" \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
    && find /root/.cache -type f -delete \
    && find /opt/venv -type d -name '__pycache__' -exec rm -rf {} + \
    && find /opt/venv -type f -name '*.pyc' -delete \
    && find /opt/venv -type d -name '*.pyc' -exec rm -rf {} + \
    && rm -rf /tmp/* /var/tmp/*

# ===================================
# Runtime stage
# ===================================
FROM python:3.11-slim-bookworm

# Set environment variables
ENV \
    # Python settings
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    # PIP settings
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    # Application settings
    VENV_PATH="/opt/venv" \
    APP_HOME="/app" \
    # Gunicorn settings
    GUNICORN_WORKERS="4" \
    GUNICORN_THREADS="2" \
    GUNICORN_TIMEOUT="120" \
    GUNICORN_KEEPALIVE="5" \
    GUNICORN_MAX_REQUESTS="1000" \
    GUNICORN_MAX_REQUESTS_JITTER="50" \
    # Port settings
    PORT="8080" \
    # Google Cloud settings
    GOOGLE_APPLICATION_CREDENTIALS="/app/service-account-key.json"

ENV APP_USER=appuser
ENV APP_GROUP=appgroup

ENV RUNTIME_DEPS="netcat-openbsd curl"

# Install system dependencies
RUN set -ex \
    && apt-get update \
    && apt-get install -y --no-install-recommends $RUNTIME_DEPS \
    && rm -rf /var/lib/apt/lists/*

# Create user and group after installing dependencies
RUN groupadd -r $APP_GROUP && useradd -r -g $APP_GROUP $APP_USER

# Create necessary directories and set ownership
RUN mkdir -p $APP_HOME \
    && chown -R $APP_USER:$APP_GROUP $APP_HOME

# Copy Python dependencies from builder
COPY --from=builder --chown=$APP_USER:$APP_GROUP ${VENV_PATH} ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:${PATH}"

# Set the working directory
WORKDIR $APP_HOME

# Copy the application code with proper ownership
# Remove .env to prevent it from overriding Cloud Run env vars
COPY --chown=$APP_USER:$APP_GROUP . .
RUN rm -f /app/.env || true

# Copy the entrypoint script
COPY --chown=$APP_USER:$APP_GROUP docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set file permissions
RUN chmod -R 755 /usr/local/bin/docker-entrypoint.sh \
    && chmod -R 755 $APP_HOME \
    && chown -R $APP_USER:$APP_GROUP $APP_HOME

# Switch to non-root user
USER $APP_USER
USER $APP_USER

# Expose the default port for Cloud Run and local Docker
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Set the entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Set the command to run the application with Gunicorn
ENV PORT=8080
CMD exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers ${GUNICORN_WORKERS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --threads ${GUNICORN_THREADS} \
    --timeout ${GUNICORN_TIMEOUT} \
    --keep-alive ${GUNICORN_KEEPALIVE} \
    --max-requests ${GUNICORN_MAX_REQUESTS} \
    --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER} \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --worker-tmp-dir /dev/shm \
    --preload \
    app.main:app
