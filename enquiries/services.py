
from datetime import timedelta

from hotels.models import Hotel
from django.db import transaction
from .models import HotelMatch

def normalize_name(value):
    """Make facility names comparable."""
    return str(value).strip().replace("_", " ").casefold()


def has_required_facilities(hotel, room_type, required_facilities):
    """Check that all requested facilities are available."""

    available = set()

    # Hotel-level facilities
    for name in hotel.hotel_facilities.values_list(
        "facility__name", flat=True
    ):
        available.add(normalize_name(name))

    # Room-level facilities
    for name in room_type.facilities.values_list("name", flat=True):
        available.add(normalize_name(name))

    # Services included with the room
    for service in room_type.included_services:
        available.add(normalize_name(service))

    # Breakfast is a special room-level feature
    if room_type.breakfast_included:
        available.add("breakfast")

    required = {
        normalize_name(item)
        for item in required_facilities
    }

    return required.issubset(available)


def get_stay_dates(check_in, check_out):
    """Return every overnight date, excluding checkout day."""

    dates = []
    current_date = check_in

    while current_date < check_out:
        dates.append(current_date)
        current_date += timedelta(days=1)

    return dates


def find_matching_hotel_rooms(requirement):
    """
    Find hotel and room-type combinations that satisfy
    a traveller's requirements.

    This function does not save HotelMatch records yet.
    """

    hotels = Hotel.objects.filter(
        country__iexact=requirement.country,
        city__iexact=requirement.city,
        status=Hotel.Status.ACTIVE,
        is_verified=True,
        is_deleted=False,
        organisation__status="active",
    ).select_related(
        "organisation"
    ).prefetch_related(
        "room_types__facilities",
        "room_types__availability_records",
        "hotel_facilities__facility",
    )

    # Optional location filters
    if requirement.province:
        hotels = hotels.filter(
            province__iexact=requirement.province
        )

    if requirement.area:
        hotels = hotels.filter(
            area__iexact=requirement.area
        )

    # Optional hotel preferences
    if requirement.preferred_hotel_types:
        hotels = hotels.filter(
            hotel_type__in=requirement.preferred_hotel_types
        )

    if requirement.minimum_star_rating is not None:
        hotels = hotels.filter(
            star_rating__gte=requirement.minimum_star_rating
        )

    stay_dates = get_stay_dates(
        requirement.check_in_date,
        requirement.check_out_date
    )

    candidates = []

    for hotel in hotels:

        for room_type in hotel.room_types.all():

            if not room_type.is_active:
                continue

            # Check room capacity across all requested rooms
            if room_type.adult_capacity * requirement.rooms < requirement.adults:
                continue

            if room_type.child_capacity * requirement.rooms < requirement.children:
                continue

            total_guests = requirement.adults + requirement.children

            if room_type.max_occupancy * requirement.rooms < total_guests:
                continue

            # Currency must match
            if room_type.currency.upper() != requirement.currency.upper():
                continue

            # Check requested facilities
            if not has_required_facilities(
                hotel,
                room_type,
                requirement.required_facilities
            ):
                continue

            # Check availability and daily prices
            availability_by_date = {
                record.date: record
                for record in room_type.availability_records.all()
            }

            nightly_prices = []
            available_for_all_nights = True

            for stay_date in stay_dates:

                record = availability_by_date.get(stay_date)

                if (
                    record is None
                    or not record.is_available
                    or record.available_rooms < requirement.rooms
                ):
                    available_for_all_nights = False
                    break

                nightly_prices.append(record.price_per_night)

            if not available_for_all_nights:
                continue

            # Calculate the total price for all requested rooms
            nightly_totals = [
                price * requirement.rooms
                for price in nightly_prices
            ]

            # Every night's total must satisfy the budget
            if requirement.min_budget_per_night is not None:
                if any(
                    price < requirement.min_budget_per_night
                    for price in nightly_totals
                ):
                    continue

            if requirement.max_budget_per_night is not None:
                if any(
                    price > requirement.max_budget_per_night
                    for price in nightly_totals
                ):
                    continue

            # Use the highest nightly total as a conservative estimate
            estimated_price = max(nightly_totals)

            candidates.append({
                "hotel": hotel,
                "room_type": room_type,
                "estimated_price_per_night": estimated_price,
                "currency": room_type.currency,
            })

    return candidates

def calculate_match_score(requirement, candidate):
    """
    Calculate a normalized match score from 0 to 100.
    Missing optional information does not unfairly reduce the score.
    """

    hotel = candidate["hotel"]
    room_type = candidate["room_type"]
    price = candidate["estimated_price_per_night"]

    earned_points = 0
    applicable_points = 0
    reasons = []

    # 1. Price competitiveness: 40 points
    if requirement.max_budget_per_night is not None:
        applicable_points += 40
        budget = requirement.max_budget_per_night

        if budget > 0:
            price_score = 40 * (
                1 - float(price / budget) * 0.5
            )
        else:
            price_score = 40 if price <= 0 else 0

        price_score = max(0, min(40, price_score))
        earned_points += price_score

        reasons.append(
            f"Within budget at {candidate['currency']} {price} per night"
        )

    # 2. Hotel star rating: 20 points
    if hotel.star_rating is not None:
        applicable_points += 20
        star_score = (hotel.star_rating / 5) * 20
        earned_points += star_score

        reasons.append(f"{hotel.star_rating}-star hotel")

    # 3. Room capacity fit: 15 points
    applicable_points += 15

    required_guests = requirement.adults + requirement.children
    available_capacity = room_type.max_occupancy * requirement.rooms

    capacity_score = (
        required_guests / available_capacity
    ) * 15

    earned_points += capacity_score

    reasons.append(
        f"Room capacity accommodates {required_guests} guests"
    )

    # 4. Location fit: 10 points
    if requirement.area:
        applicable_points += 10

        if hotel.area.strip().casefold() == requirement.area.strip().casefold():
            earned_points += 10
            reasons.append(f"Located in {hotel.area}")

    # 5. Preferred hotel type: 5 points
    if requirement.preferred_hotel_types:
        applicable_points += 5

        if hotel.hotel_type in requirement.preferred_hotel_types:
            earned_points += 5
            reasons.append(
                f"Preferred hotel type: {hotel.hotel_type}"
            )

    # 6. Additional amenities: 10 points
    applicable_points += 10

    available = set()

    for name in hotel.hotel_facilities.values_list(
        "facility__name", flat=True
    ):
        available.add(normalize_name(name))

    for name in room_type.facilities.values_list("name", flat=True):
        available.add(normalize_name(name))

    for service in room_type.included_services:
        available.add(normalize_name(service))

    if room_type.breakfast_included:
        available.add("breakfast")

    required = {
        normalize_name(item)
        for item in requirement.required_facilities
    }

    extra_amenities = available - required
    extra_score = min(len(extra_amenities), 5) * 2

    earned_points += extra_score

    if extra_amenities:
        reasons.append(
            "Additional amenities: "
            + ", ".join(sorted(extra_amenities))
        )

    # Normalize the score to 100
    final_score = round(
        (earned_points / applicable_points) * 100
    )

    return {
        "match_score": final_score,
        "match_reasons": reasons,
    }

def generate_hotel_matches(requirement):
    """
    Find eligible hotel rooms, score them, and save the
    best room-type match for each hotel.

    Existing HotelMatch records are updated rather than duplicated.
    """

    candidates = find_matching_hotel_rooms(requirement)

    # Keep only the best-scoring room type for each hotel
    best_candidates = {}

    for candidate in candidates:
        hotel = candidate["hotel"]
        score_data = calculate_match_score(requirement, candidate)

        hotel_id = hotel.id

        if hotel_id not in best_candidates:
            best_candidates[hotel_id] = (candidate, score_data)
            continue

        current_candidate, current_score = best_candidates[hotel_id]

        new_score = score_data["match_score"]
        old_score = current_score["match_score"]

        new_price = candidate["estimated_price_per_night"]
        old_price = current_candidate["estimated_price_per_night"]

        if new_score > old_score or (
            new_score == old_score and new_price < old_price
        ):
            best_candidates[hotel_id] = (candidate, score_data)

    saved_matches = []

    # Save all results in one database transaction
    with transaction.atomic():

        for candidate, score_data in best_candidates.values():

            match, created = HotelMatch.objects.update_or_create(
                requirement=requirement,
                hotel=candidate["hotel"],
                defaults={
                    "matched_room_type": candidate["room_type"],
                    "match_score": score_data["match_score"],
                    "match_reasons": score_data["match_reasons"],
                    "estimated_price_per_night": (
                        candidate["estimated_price_per_night"]
                    ),
                    "currency": candidate["currency"],
                }
            )

            saved_matches.append(match)

    return sorted(
        saved_matches,
        key=lambda match: (
            -match.match_score,
            match.estimated_price_per_night
        )
    )
