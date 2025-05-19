#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print section header
print_section() {
    echo -e "\n${YELLOW}==> $1${NC}"
}

# Function to print status
print_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK]${NC} $1"
    else
        echo -e "${RED}[ERROR]${NC} $1"
        exit 1
    fi
}

# Check for required tools
print_section "Checking required tools"

# Check for Python
if command_exists python3 && python3 -c "import sys; sys.exit(sys.version_info < (3, 10))"; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
    print_status "Python 3.10+ is installed"
else
    echo -e "${RED}Python 3.10+ is required but not installed.${NC}"
    echo "Please install Python 3.10 or later and try again."
    exit 1
fi

# Check for Docker
if command_exists docker; then
    print_status "Docker is installed"
else
    echo -e "${RED}Docker is required but not installed.${NC}"
    echo "Please install Docker and try again: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for Docker Compose
if command_exists docker-compose || (command_exists docker && docker compose version >/dev/null 2>&1); then
    print_status "Docker Compose is installed"
else
    echo -e "${RED}Docker Compose is required but not installed.${NC}"
    echo "Please install Docker Compose and try again: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check for Poetry
if command_exists poetry; then
    print_status "Poetry is installed"
else
    echo -e "${YELLOW}Poetry is not installed. Installing...${NC}"
    curl -sSL https://install.python-poetry.org | $PYTHON_CMD -
    export PATH="$HOME/.local/bin:$PATH"
    print_status "Poetry installed successfully"
fi

# Set up virtual environment
print_section "Setting up Python virtual environment"
poetry install --with dev --no-interaction
print_status "Dependencies installed"

# Set up pre-commit hooks
print_section "Setting up pre-commit hooks"
poetry run pre-commit install
print_status "Pre-commit hooks installed"

# Set up environment variables
print_section "Setting up environment variables"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Created .env file from .env.example${NC}"
    echo -e "${YELLOW}Please edit the .env file with your configuration${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

# Start development services
print_section "Starting development services"
if [ -f docker-compose.override.yml ] || [ -f docker-compose.override.yaml ]; then
    echo -e "${YELLOW}docker-compose.override.yml found, using custom configuration${NC}"
fi

docker-compose up -d
print_status "Development services started"

# Wait for PostgreSQL to be ready
print_section "Waiting for PostgreSQL to be ready"
until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}PostgreSQL is ready${NC}"

# Run database migrations
print_section "Running database migrations"
alembic upgrade head
print_status "Database migrations applied"

# Print completion message
print_section "Setup complete!"
echo -e "${GREEN}✅ Development environment is ready!${NC}"
echo ""
echo "Next steps:"
echo "1. Run the development server: ${YELLOW}make dev${NC}"
echo "2. Access the API docs at: ${YELLOW}http://localhost:8000/docs${NC}"
echo "3. Run tests: ${YELLOW}make test${NC}"
echo ""
echo "To stop the development services, run: ${YELLOW}make docker-down${NC}"
