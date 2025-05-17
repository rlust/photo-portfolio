#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
COMPOSE_FILE="../docker-compose.yml"
SERVICE="app"

# Function to display help
show_help() {
    echo -e "${YELLOW}Usage: $0 [command]${NC}"
    echo ""
    echo "Available commands:"
    echo "  up               Start all services in detached mode"
    echo "  down            Stop and remove all services"
    echo "  logs            Follow logs from all services"
    echo "  logs [service]  Follow logs from a specific service"
    echo "  shell           Open a shell in the app container"
    echo "  db-shell        Open a PostgreSQL shell"
    echo "  db-reset        Reset the database (WARNING: deletes all data!)"
    echo "  test            Run tests"
    echo "  lint            Run linters"
    echo "  format          Format code"
    echo "  help            Show this help message"
}

# Function to start services
start_services() {
    echo -e "${GREEN}Starting services...${NC}"
    docker-compose -f $COMPOSE_FILE up -d
}

# Function to stop services
stop_services() {
    echo -e "${YELLOW}Stopping services...${NC}"
    docker-compose -f $COMPOSE_FILE down
}

# Function to show logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker-compose -f $COMPOSE_FILE logs -f
    else
        docker-compose -f $COMPOSE_FILE logs -f "$service"
    fi
}

# Function to open a shell in the app container
open_shell() {
    echo -e "${GREEN}Opening shell in app container...${NC}"
    docker-compose -f $COMPOSE_FILE exec $SERVICE bash
}

# Function to open a PostgreSQL shell
open_db_shell() {
    echo -e "${GREEN}Opening PostgreSQL shell...${NC}"
    docker-compose -f $COMPOSE_FILE exec db psql -U ${DB_USER:-postgres} -d ${DB_NAME:-photo_portfolio}
}

# Function to reset the database
reset_database() {
    echo -e "${RED}WARNING: This will delete all data in the database!${NC}"
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Resetting database...${NC}"
        docker-compose -f $COMPOSE_FILE down -v
        docker-compose -f $COMPOSE_FILE up -d db
        echo -e "${GREEN}Database has been reset.${NC}"
    else
        echo -e "${YELLOW}Database reset cancelled.${NC}"
    fi
}

# Function to run tests
run_tests() {
    echo -e "${GREEN}Running tests...${NC}"
    docker-compose -f $COMPOSE_FILE exec $SERVICE pytest
}

# Function to run linters
run_lint() {
    echo -e "${GREEN}Running linters...${NC}"
    docker-compose -f $COMPOSE_FILE exec $SERVICE black --check .
    docker-compose -f $COMPOSE_FILE exec $SERVICE isort --check-only .
    docker-compose -f $COMPOSE_FILE exec $SERVICE flake8 .
    docker-compose -f $COMPOSE_FILE exec $SERVICE mypy .
}

# Function to format code
format_code() {
    echo -e "${GREEN}Formatting code...${NC}"
    docker-compose -f $COMPOSE_FILE exec $SERVICE black .
    docker-compose -f $COMPOSE_FILE exec $SERVICE isort .
}

# Main command handler
case "$1" in
    up)
        start_services
        ;;
    down)
        stop_services
        ;;
    logs)
        show_logs "$2"
        ;;
    shell)
        open_shell
        ;;
    db-shell)
        open_db_shell
        ;;
    db-reset)
        reset_database
        ;;
    test)
        run_tests
        ;;
    lint)
        run_lint
        ;;
    format)
        format_code
        ;;
    help|--help|-h|*)
        show_help
        ;;
esac

exit 0
