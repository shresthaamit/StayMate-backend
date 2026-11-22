# StayMate Backend

Backend REST API for **StayMate**, an AI-powered hotel concierge platform built with Django and Django REST Framework.

## Overview

StayMate aims to simplify hotel discovery by allowing travellers to submit accommodation requirements and receive suitable hotel matches.

The platform supports hotel management, room availability, requirement matching, simulated hotel enquiries, location-based hotel discovery, and comparison of hotel results.

Future development will introduce AI-powered voice communication with hotels in Nepali and English, together with a React Native mobile application.

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

### Location-Based Hotel Discovery

- Nearby hotel search using latitude and longitude
- Distance calculation using the Haversine formula
- Configurable search radius
- Destination-based search by city or area without requiring GPS
- Map viewport/bounds search
- Support for map searches crossing the international date line
- Filters for city, area, star rating, hotel type and facilities
- Distance-based sorting for nearby hotels
- Paginated search results
- Map marker metadata containing hotel coordinates and relevant distance information

**Location privacy:** The backend accepts coordinates supplied by the client. A future mobile application must request the traveller's location permission before obtaining and sending device coordinates. Travellers can also search by destination without sharing their current location.

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
| GET | `/api/hotels/nearby/` | Search hotels near supplied coordinates |
| GET | `/api/hotels/search/` | Search hotels by city or area |
| GET | `/api/hotels/map/` | Search hotels within map boundaries |
| GET | `/api/hotels/management/hotels/` | List organisation hotels |
| GET | `/api/hotels/management/hotels/<id>/` | Retrieve managed hotel details |
| POST | `/api/hotels/management/hotels/create/` | Create a hotel |
| PUT, PATCH | `/api/hotels/management/hotels/<id>/update/` | Update a hotel |
| DELETE | `/api/hotels/management/hotels/<id>/delete/` | Delete a hotel |

### Location Search API Usage

All three location search endpoints are public and use GET requests.

#### 1. Nearby Hotel Search

**Endpoint:**

`GET /api/hotels/nearby/`

Finds hotels within a specified distance from supplied coordinates.

Required query parameters:

| Parameter | Description |
|---|---|
| `latitude` | Search centre latitude |
| `longitude` | Search centre longitude |

Optional query parameters:

| Parameter | Description |
|---|---|
| `radius_km` | Search radius in kilometres (default 10, maximum 100) |
| `city` | Filter by city |
| `area` | Filter by area |
| `min_star_rating` | Minimum hotel star rating |
| `max_star_rating` | Maximum hotel star rating |
| `hotel_type` | Filter by hotel type |
| `facility` | Filter by facility name |
| `sort_order` | Distance order: `asc` or `desc` |
| `page` | Page number |
| `page_size` | Results per page (maximum 50) |

Example:

```http
GET /api/hotels/nearby/?latitude=28.2096&longitude=83.9856&radius_km=10
```

The response includes:

- Total matching hotel count
- Pagination links
- Search coordinates
- Search radius
- Distance sorting order
- Hotel results with distance information
- Map markers with hotel coordinates and distances

#### 2. Destination-Based Hotel Search

**Endpoint:**

`GET /api/hotels/search/`

Searches hotels using a destination without requiring the traveller's GPS location.

At least one of the following parameters is required:

| Parameter | Description |
|---|---|
| `city` | Search by city |
| `area` | Search by area |
| `page` | Page number |
| `page_size` | Results per page (maximum 50) |

Example:

```http
GET /api/hotels/search/?city=Pokhara
```

Another example:

```http
GET /api/hotels/search/?city=Pokhara&area=Lakeside
```

Hotels without latitude and longitude can still appear in destination search results. Only hotels with coordinates are included in the map marker data.

#### 3. Map Bounds Hotel Search

**Endpoint:**

`GET /api/hotels/map/`

Finds hotels inside the currently visible map boundaries.

Required query parameters:

| Parameter | Description |
|---|---|
| `north` | Northern latitude boundary |
| `south` | Southern latitude boundary |
| `east` | Eastern longitude boundary |
| `west` | Western longitude boundary |

Optional query parameters:

| Parameter | Description |
|---|---|
| `city` | Filter by city |
| `area` | Filter by area |
| `min_star_rating` | Minimum hotel star rating |
| `max_star_rating` | Maximum hotel star rating |
| `hotel_type` | Filter by hotel type |
| `facility` | Filter by facility name |
| `page` | Page number |
| `page_size` | Results per page (maximum 50) |

Example:

```http
GET /api/hotels/map/?north=28.30&south=28.10&east=84.10&west=83.80
```

The response includes:

- Total matching hotel count
- Pagination links
- Map boundary information
- Map markers containing hotel IDs, names and coordinates
- Paginated hotel results

The endpoint also supports map boundaries crossing the international date line, where the western longitude is greater than the eastern longitude.

**Map integration note:** These APIs provide hotel coordinates and map marker data. Map rendering, device location permissions, interactive map movement and route directions will be implemented in the mobile application and subsequent mapping integration.

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

Protected endpoints require authentication. Public hotel discovery endpoints are accessible without authentication.

## Pagination

Location search endpoints support page-number pagination.

- Default page size: 10
- Configurable using `page_size`
- Maximum page size: 50
- Responses include `count`, `next`, `previous` and `results`

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

**Latest verified test result:** 99 tests passed.

## Security

- JWT-based authentication
- Owner-scoped access to traveller requirements and results
- Organisation-based access control
- Login and phone OTP request throttling
- OTP expiration and failed-attempt limits
- Input validation for API requests
- Sensitive configuration, local databases, uploaded media and virtual environments excluded from version control
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
- [x] Nearby hotel search
- [x] Destination-based hotel search
- [x] Map viewport/bounds hotel search
- [x] Location search pagination and filtering
- [x] Location API documentation
- [ ] Provider-independent AI calling architecture
- [ ] Research Nepal-compatible AI calling providers
- [ ] React Native mobile application
- [ ] Interactive map and device location integration
- [ ] Real AI-powered hotel voice enquiries in Nepali and English
- [ ] Production deployment and end-to-end testing

## Project Status

**Active development.**

The core backend features for authentication, hotel management, traveller requirements, hotel matching, simulated enquiries, results filtering, sorting, comparison and location-based hotel discovery have been implemented.

The latest full backend test run completed successfully with 99 passing tests.

Real hotel phone calls, the React Native application and interactive map interface are planned for subsequent development stages.
