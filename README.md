# Cynosure - Legal Information Platform

Intelligent legal information platform for real-time access to court data in Nigeria.

## Features

- **Real-time Court Data**: Access cause lists, case information, and court schedules
- **Case Tracking**: Follow cases and receive updates on hearings and adjournments
- **Notification System**: Multi-channel notifications (WebSocket, Push, Email)
- **Legal Repository**: Access court rules, practice directions, and legal documents
- **E-Filing**: Electronic filing system for court documents
- **Search**: Powerful search across cases, cause lists, and documents
- **Admin Dashboard**: Analytics and system management

## Tech Stack

- **Backend**: Django 4.2, Django REST Framework
- **Real-time**: Django Channels, Redis
- **Database**: PostgreSQL 15
- **Task Queue**: Celery, Celery Beat
- **Caching**: Redis
- **API Docs**: drf-spectacular (OpenAPI 3.0)
- **Deployment**: Docker, Nginx, Gunicorn

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/cynosure.git
cd cynosure
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create superuser:
```bash
python manage.py createsuperuser
```

7. Run development server:
```bash
python manage.py runserver
```

### Docker Setup

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

2. Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

3. Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

## API Documentation

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Project Structure

```
cynosure/
├── apps/
│   ├── authentication/   # User auth, JWT, profiles
│   ├── courts/          # Courts, divisions, panels
│   ├── judges/          # Judge profiles, availability
│   ├── cases/           # Case tracking, hearings
│   ├── cause_lists/     # Cause lists, entries
│   ├── notifications/   # Multi-channel notifications
│   ├── search/          # Search functionality
│   ├── repository/      # Legal document repository
│   ├── efiling/         # E-filing system
│   ├── firms/           # Law firm management
│   ├── adminpanel/      # Admin dashboard
│   ├── scraping/        # Court data scrapers
│   ├── core/            # Health checks, utilities
│   └── common/          # Shared models, utils
├── config/
│   ├── settings/        # Django settings
│   ├── urls.py          # URL configuration
│   ├── asgi.py          # ASGI config (WebSockets)
│   ├── wsgi.py          # WSGI config
│   └── celery.py        # Celery configuration
├── nginx/               # Nginx configuration
├── templates/           # Email templates
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── manage.py
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup/` - User registration
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/logout/` - User logout
- `POST /api/v1/auth/token/refresh/` - Refresh JWT token
- `POST /api/v1/auth/password-reset/` - Request password reset
- `GET /api/v1/auth/profile/` - Get user profile

### Courts
- `GET /api/v1/courts/` - List courts
- `GET /api/v1/courts/{id}/` - Get court details
- `POST /api/v1/courts/{id}/follow/` - Follow court
- `GET /api/v1/courts/{id}/divisions/` - Get court divisions

### Judges
- `GET /api/v1/judges/` - List judges
- `GET /api/v1/judges/{id}/` - Get judge details
- `GET /api/v1/judges/{id}/availability/` - Get judge availability
- `GET /api/v1/judges/{id}/cause-lists/` - Get judge's cause lists

### Cause Lists
- `GET /api/v1/cause-lists/` - List cause lists
- `GET /api/v1/cause-lists/daily/` - Get daily summary
- `GET /api/v1/cause-lists/by-judge/` - Get by judge
- `GET /api/v1/cause-lists/future/` - Get upcoming cause lists

### Cases
- `GET /api/v1/cases/` - List cases
- `GET /api/v1/cases/search/` - Search cases
- `GET /api/v1/cases/{id}/timeline/` - Get case timeline
- `POST /api/v1/cases/{id}/follow/` - Follow case

### Notifications
- `GET /api/v1/notifications/` - List notifications
- `GET /api/v1/notifications/counts/` - Get notification counts
- `POST /api/v1/notifications/mark-read/` - Mark as read

### Search
- `GET /api/v1/search/` - Global search
- `GET /api/v1/search/cases/` - Search cases
- `GET /api/v1/search/cause-lists/` - Search cause lists

## WebSocket Endpoints

- `ws://localhost:8001/ws/cause-lists/` - Cause list updates
- `ws://localhost:8001/ws/notifications/` - User notifications

## Running Tests

```bash
pytest
# or with coverage
pytest --cov=apps --cov-report=html
```

## License

Proprietary - All rights reserved
