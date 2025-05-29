# Optimized Frontend Dockerfile for PhotoPortfolio

# BUILD STAGE
# Use specific Node version for predictability and smaller base image
FROM node:20-alpine as build

# Set working directory
WORKDIR /app

# Environment variables for better build performance
ENV NODE_ENV=production \
    NPM_CONFIG_LOGLEVEL=error \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false

# Copy package files first for better layer caching
COPY package.json package-lock.json ./

# Install dependencies with clean cache
RUN npm ci --silent && \
    npm cache clean --force

# Copy only necessary source files
COPY public/ ./public/
COPY src/ ./src/
# Copy any other configuration files that exist
COPY *.json ./

# Build the application with optimizations
RUN npm run build

# RUNTIME STAGE
# Use the lightweight nginx alpine image for production
FROM nginx:stable-alpine

# Set working directory
WORKDIR /usr/share/nginx/html

# Copy only the build artifacts
COPY --from=build /app/build ./

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose the default port for Cloud Run and local Docker
EXPOSE 8080

# Add health check capability
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost:8080/ || exit 1

# Start Nginx with daemon off
CMD ["nginx", "-g", "daemon off;"]
