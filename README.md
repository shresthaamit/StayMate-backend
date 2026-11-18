# StayMate Backend

Backend REST API for **StayMate**, an AI-powered hotel concierge platform built with Django and Django REST Framework.

## Overview

StayMate aims to simplify hotel discovery by allowing travellers to submit accommodation requirements and receive suitable hotel matches.

The platform supports hotel management, room availability, requirement matching, simulated hotel enquiries, and comparison of hotel results. Future development will introduce AI-powered voice communication with hotels in Nepali and English.

## Technology Stack

- Python
- Django
- Django REST Framework
- Django REST Framework Simple JWT
- SQLite (development database)

## Current Features

### Authentication and Accounts
- User registration and authentication
- JWT access and refresh tokens
- User profile API
- Phone OTP verification endpoints

### Hotel Management
- Organisation and membership management
- Role-based hotel management permissions
- Hotel profile management
- Hotel facilities and contacts
- Room types and room availability
- Hotel image management
- Public hotel listing and detail APIs
- Hotel verification and status filtering

### Traveller Requirements and Matching
- Create and manage traveller requirements
- Destination, dates, guest count and budget information
- Preferred hotel types and required facilities
- Automated hotel matching
- Match scoring and recommendation reasons

### Simulated Hotel Enquiries
- Create hotel call attempts
- Simulate hotel responses
- Record conversation transcripts
- Collect availability, pricing and service information
- Track call status and retry attempts

### Results and Comparison
- Retrieve matched hotel results
- Filter by price, star rating, hotel type and facilities
- Sort by price, rating and match score
- Compare 2–4 selected hotel matches
- Retrieve the latest simulated call information

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/accounts/register/` | User registration |
| POST | `/api/accounts/login/` | User login |
| POST | `/api/accounts/token/refresh/` | Refresh JWT token |
| GET | `/api/accounts/me/` | Retrieve authenticated user profile |
| GET | `/api/hotels/` | List public verified hotels |
| GET | `/api/hotels/<id>/` | Retrieve hotel details |
| GET, POST | `/api/enquiries/` | List or create traveller requirements |
| GET | `/api/enquiries/<id>/` | Retrieve a requirement |
| POST | `/api/enquiries/<id>/matches/` | Generate hotel matches |
| GET | `/api/enquiries/<id>/results/` | Retrieve filtered and sorted results |
| GET | `/api/enquiries/<id>/compare/` | Compare selected hotel matches |
| GET, POST | `/api/enquiries/matches/<id>/calls/` | List or create hotel call attempts |
| POST | `/api/enquiries/calls/<id>/simulate/` | Run a simulated hotel enquiry |

All protected endpoints require authentication unless otherwise specified.

## Project Structure

```text
backend/
├── accounts/
├── config/
├── hotels/
├── enquiries/
├── manage.py
├── requirements.txt
└── README.md
```

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

## Running Tests

Run the complete Django test suite:

```bash
python manage.py test
```

**Latest verified test result:** 43 tests passed.

## Security

- JWT-based authentication
- Owner-scoped access to traveller requirements and results
- Organisation-based access control
- Sensitive configuration, local databases, uploaded media, and virtual environments excluded from version control

## Development Roadmap

- End-to-end API testing
- Backend security and error handling improvements
- API documentation and final verification
- React Native mobile application
- Provider-independent AI calling architecture
- Real AI-powered hotel voice enquiries in Nepali and English

## Project Status

**Active development.**

The core backend features for authentication, hotel management, traveller requirements, hotel matching, simulated enquiries, results filtering, sorting, and comparison have been implemented.

The latest full test run completed successfully with 43 passing tests.
