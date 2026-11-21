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
- Phone OTP verification endpoints (development mode; OTP is printed in the backend terminal)

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

**Note:** Hotel enquiries are currently simulated. No real phone calls are made to hotels.

### Results and Comparison

- Retrieve matched hotel results
- Filter by price, star rating, hotel type and facilities
- Sort by price, rating and match score
- Compare 2–4 selected hotel matches
- Retrieve the latest simulated call information

## API Endpoints

### Accounts

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/accounts/register/` | User registration |
| POST | `/api/accounts/login/` | User login |
| POST | `/api/accounts/phone/request-otp/` | Request phone OTP |
| POST | `/api/accounts/phone/verify-otp/` | Verify phone OTP |
| GET | `/api/accounts/me/` | Retrieve authenticated user profile |
| POST | `/api/accounts/token/refresh/` | Refresh JWT token |

### Hotels

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/hotels/` | List public verified hotels |
| GET | `/api/hotels/<id>/` | Retrieve hotel details |
| GET | `/api/hotels/management/hotels/` | List organisation hotels |
| GET | `/api/hotels/management/hotels/<id>/` | Retrieve managed hotel details |
| POST | `/api/hotels/management/hotels/create/` | Create a hotel |
| PUT, PATCH | `/api/hotels/management/hotels/<id>/update/` | Update a hotel |
| DELETE | `/api/hotels/management/hotels/<id>/delete/` | Delete a hotel |

### Traveller Requirements and Matching

| Method | Endpoint | Description |
|---|---|---|
| GET, POST | `/api/enquiries/` | List or create traveller requirements |
| GET | `/api/enquiries/<id>/` | Retrieve a requirement |
| POST | `/api/enquiries/<id>/matches/` | Generate hotel matches |

### Hotel Enquiries

| Method | Endpoint | Description |
|---|---|---|
| GET, POST | `/api/enquiries/matches/<match_id>/calls/` | List or create hotel call attempts |
| GET | `/api/enquiries/calls/<id>/` | Retrieve a hotel call |
| POST | `/api/enquiries/calls/<id>/simulate/` | Run a simulated hotel enquiry |

### Results and Comparison

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/enquiries/<requirement_id>/results/` | Retrieve filtered and sorted results |
| GET | `/api/enquiries/<requirement_id>/compare/` | Compare selected hotel matches |

All protected endpoints require authentication. Public hotel listing and detail endpoints are accessible without authentication.

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

5. Generate a secure Django secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

6. Create a `.secret_key` file in the backend directory and paste the generated key into it.
7. Apply database migrations:

```bash
python manage.py migrate
```

8. Create a superuser:

```bash
python manage.py createsuperuser
```

9. Start the development server:

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
- Login and phone OTP request throttling
- OTP expiration and failed-attempt limits
- Sensitive configuration, local databases, uploaded media, and virtual environments excluded from version control
- Environment-based configuration for production settings

## Development Roadmap

- [x] Backend authentication and account management
- [x] Hotel and organisation management
- [x] Traveller requirements and hotel matching
- [x] Simulated hotel enquiries
- [x] Results filtering, sorting and comparison
- [x] Backend security and error-handling improvements
- [x] Automated testing and end-to-end API verification
- [x] Backend configuration and repository security review
- [ ] Complete API documentation
- [ ] React Native mobile application
- [ ] Provider-independent AI calling architecture
- [ ] Real AI-powered hotel voice enquiries in Nepali and English

## Project Status

**Active development.**

The core backend features for authentication, hotel management, traveller requirements, hotel matching, simulated enquiries, results filtering, sorting, and comparison have been implemented.

The latest full test run completed successfully with 43 passing tests.