.PHONY: help install dev test lint format clean docker-build docker-run

# Default target
help:
	@echo "Manus Web Agent - Available Commands:"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make install-dev  - Install dev dependencies"
	@echo "  make dev          - Run development server with auto-reload"
	@echo "  make run          - Run production server"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-integration - Run integration tests (requires services)"
	@echo "  make lint         - Run linting (ruff)"
	@echo "  make format       - Format code (ruff)"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run with docker-compose"
	@echo "  make docker-stop  - Stop docker-compose services"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pip install -r tests/requirements.txt

# Development
run:
	./run.sh

dev:
	./dev.sh

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest tests/ -v -m "not integration"

test-integration:
	pytest tests/ -v -m "integration"

test-cov:
	pytest tests/ --cov=src/manus_web_agent --cov-report=html --cov-report=term

# Linting and formatting
lint:
	ruff check src/
	mypy src/

format:
	ruff format src/
	ruff check --fix src/

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Docker
docker-build:
	docker build -t manus-web-agent:latest .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f app

# Database
db-start:
	docker-compose up -d mongodb redis

db-stop:
	docker-compose stop mongodb redis

db-reset:
	docker-compose down -v
	docker-compose up -d mongodb redis
