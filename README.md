# StayMate Backend

Backend REST API for **StayMate**, an AI-powered hotel concierge platform built with Django and Django REST Framework.

## Overview

StayMate aims to connect travellers with hotels through a central platform, providing hotel information, room details, availability, and concierge services.

## Technology Stack

- Python
- Django
- Django REST Framework
- Django REST Framework Simple JWT
- SQLite (development database)

## Current Features

- User registration and authentication
- JWT access and refresh tokens
- User profile API
- Phone OTP verification endpoints
- Organisation and membership management
- Hotel profile management
- Hotel facilities and contacts
- Room types and room availability
- Hotel image management
- Public hotel listing and detail APIs
- Hotel verification status filtering

## Project Structure

```text
backend/
├── accounts/
├── config/
├── hotels/
├── manage.py
├── requirements.txt
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/accounts/register/` | User registration |
| POST | `/api/accounts/token/` | Obtain JWT tokens |
| POST | `/api/accounts/token/refresh/` | Refresh JWT token |
| GET | `/api/accounts/me/` | Retrieve authenticated user profile |
| GET | `/api/hotels/` | List public verified hotels |
| GET | `/api/hotels/<id>/` | Retrieve hotel details |

## Local Setup

1. Clone the repository.
2. Navigate into the backend directory.
3. Create and activate a Python virtual environment.
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Create a `.secret_key` file containing a Django secret key.
6. Apply database migrations:

```bash
python manage.py migrate
```

7. Create a superuser:

```bash
python manage.py createsuperuser
```

8. Start the development server:

```bash
python manage.py runserver
```

## Development Roadmap

- Hotel owner and manager APIs
- Organisation-based tenant access control
- Hotel verification workflow
- Room and availability management APIs
- Booking management
- AI-powered hotel concierge features

## Security

Sensitive configuration, local databases, uploaded media, and virtual environments are excluded from version control.

## Project Status

Under active development.
