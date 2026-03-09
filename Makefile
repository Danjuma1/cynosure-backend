# Makefile for Cynosure Backend

.PHONY: help install dev test lint format migrate shell run celery beat docker-up docker-down clean

help:
	@echo "Cynosure Backend Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install     Install dependencies"
	@echo "  dev         Install dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  run         Run development server"
	@echo "  shell       Open Django shell"
	@echo "  migrate     Run migrations"
	@echo "  makemigrations  Create new migrations"
	@echo ""
	@echo "Testing:"
	@echo "  test        Run all tests"
	@echo "  test-cov    Run tests with coverage"
	@echo "  lint        Run linter"
	@echo "  format      Format code"
	@echo ""
	@echo "Celery:"
	@echo "  celery      Start Celery worker"
	@echo "  beat        Start Celery beat"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up   Start all services with Docker"
	@echo "  docker-down Stop all Docker services"
	@echo "  docker-logs View Docker logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean       Remove cache files"

# Setup
install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install black isort flake8

# Development
run:
	python manage.py runserver

shell:
	python manage.py shell_plus

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

collectstatic:
	python manage.py collectstatic --noinput

createsuperuser:
	python manage.py createsuperuser

# Testing
test:
	pytest

test-cov:
	pytest --cov=apps --cov-report=html --cov-report=term-missing

test-fast:
	pytest -x -q

lint:
	flake8 apps/ --max-line-length=120 --exclude=migrations

format:
	black apps/
	isort apps/

# Celery
celery:
	celery -A config worker -l info -Q default,notifications,scraping,search

beat:
	celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Docker
docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec web python manage.py shell

docker-migrate:
	docker-compose exec web python manage.py migrate

# Database
db-reset:
	python manage.py reset_db --noinput
	python manage.py migrate

db-seed:
	python manage.py loaddata fixtures/initial_data.json

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

# Production
gunicorn:
	gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 2 config.wsgi:application

daphne:
	daphne -b 0.0.0.0 -p 8001 config.asgi:application
