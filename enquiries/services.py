from enquiries.calling.conversation import HotelConversationEngine
from datetime import timedelta
from django.utils import timezone
from hotels.models import RoomAvailability
from .models import HotelCall, HotelMatch
from hotels.models import Hotel,HotelContact
from django.db import transaction


def normalize_name(value):
    """Make facility names comparable."""
    return str(value).strip().replace("_", " ").casefold()


def normalize_call_language(value):
    """Convert supported language names into internal language codes."""

    if not value:
        return None

    language = str(value).strip().casefold()

    language_codes = {
        "english": "en",
        "en": "en",
        "nepali": "ne",
        "ne": "ne",
        "नेपाली": "ne",
    }

    return language_codes.get(language)


def resolve_hotel_contact(hotel):
    """
    Select the most appropriate hotel contact and calling number.

    Priority:
    1. Primary reservation contact
    2. Other reservation contacts
    3. Primary receptionist
    4. Other receptionists
    5. Other primary contacts
    6. Other contacts
    7. Hotel alternative phone
    8. Hotel main phone
    """

    contacts = list(
        HotelContact.objects.filter(hotel=hotel).order_by("id")
    )

    def contact_priority(contact):
        if contact.role == HotelContact.ContactRole.RESERVATION:
            return (0 if contact.is_primary else 1, contact.id)

        if contact.role == HotelContact.ContactRole.RECEPTIONIST:
            return (2 if contact.is_primary else 3, contact.id)

        return (4 if contact.is_primary else 5, contact.id)

    # Sort contacts by role and primary status.
    contacts.sort(key=contact_priority)

    selected_contact = next(
        (
            contact
            for contact in contacts
            if contact.phone_number
            and contact.phone_number.strip()
        ),
        None,
    )

    if selected_contact:
        phone_number = selected_contact.phone_number.strip()
        contact_name = selected_contact.name
        contact_role = selected_contact.role
        contact_id = selected_contact.id
        contact_email = (
            selected_contact.email.strip()
            or hotel.contact_email
        )
        source = "hotel_contact"

        language = (
            normalize_call_language(
                selected_contact.preferred_language
            )
            or normalize_call_language(hotel.preferred_language)
            or "en"
        )

    else:
        phone_number = (
            hotel.alternative_phone.strip()
            or hotel.contact_phone.strip()
        )

        contact_name = None
        contact_role = None
        contact_id = None
        contact_email = hotel.contact_email
        source = (
            "hotel_alternative_phone"
            if hotel.alternative_phone.strip()
            else "hotel_main_phone"
        )

        language = (
            normalize_call_language(hotel.preferred_language)
            or "en"
        )

    if not phone_number:
        return {
            "available": False,
            "contact_id": None,
            "contact_name": None,
            "contact_role": None,
            "phone_number": None,
            "email": None,
            "language": language,
            "source": None,
        }

    return {
        "available": True,
        "contact_id": contact_id,
        "contact_name": contact_name,
        "contact_role": contact_role,
        "phone_number": phone_number,
        "email": contact_email,
        "language": language,
        "source": source,
    }



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

    Updates existing matches, removes stale shortlisted matches,
    and preserves matches that have progressed beyond shortlisting.
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

    # Save results and clean stale shortlisted matches atomically
    with transaction.atomic():

        matched_hotel_ids = set(best_candidates.keys())

        stale_matches = HotelMatch.objects.filter(
            requirement=requirement,
            status=HotelMatch.Status.SHORTLISTED
        )

        if matched_hotel_ids:
            stale_matches = stale_matches.exclude(
                hotel_id__in=matched_hotel_ids
            )

        stale_matches.delete()

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

def run_simulated_hotel_call(call):
    """
    Execute a simulated conversation using information stored
    in the hotel's database. No real phone call is made.
    """

    if call.status != HotelCall.Status.QUEUED:
        raise ValueError("Only queued calls can be executed.")

    match = call.hotel_match
    requirement = match.requirement
    hotel = match.hotel
    room = match.matched_room_type

    now = timezone.now()

    call.status = HotelCall.Status.IN_PROGRESS
    call.started_at = now
    call.save(update_fields=["status", "started_at", "updated_at"])

    transcript = []

    def add_message(role, message):
        transcript.append({
            "role": role,
            "message": message,
            "timestamp": timezone.now().isoformat(),
        })
    conversation_engine = HotelConversationEngine(call)

    questions = {
        item["key"]: item["message"]
        for item in conversation_engine.build_questions()
    }

    language = conversation_engine.language

    replies = {
        "missing_room": {
            "en": "Room information is not available for this enquiry.",
            "ne": "यस सोधपुछका लागि कोठाको जानकारी उपलब्ध छैन।",
        },
        "unavailable": {
            "en": (
                "The requested room availability could not be confirmed "
                "for every night of the stay."
            ),
            "ne": (
                "बसाइको सबै रातका लागि अनुरोध गरिएको कोठाको उपलब्धता "
                "पुष्टि गर्न सकिएन।"
            ),
        },
        "available": {
            "en": "Yes, the requested room is available for those dates.",
            "ne": "हो, अनुरोध गरिएका मितिहरूमा कोठा उपलब्ध छ।",
        },
        "price_unknown": {
            "en": "The price could not be confirmed.",
            "ne": "मूल्य पुष्टि गर्न सकिएन।",
        },
        "breakfast_yes": {
            "en": "Yes, breakfast is included.",
            "ne": "हो, बिहानको खाना समावेश छ।",
        },
        "breakfast_no": {
            "en": "Breakfast is not included according to our records.",
            "ne": "हाम्रो अभिलेखअनुसार बिहानको खाना समावेश छैन।",
        },
        "airport_yes": {
            "en": "Airport pickup is listed among the hotel's services.",
            "ne": "होटलको सेवामा विमानस्थल पिकअप समावेश छ।",
        },
        "airport_unknown": {
            "en": "Airport pickup information is not recorded.",
            "ne": "विमानस्थल पिकअपसम्बन्धी जानकारी उपलब्ध छैन।",
        },
        "times_unknown": {
            "en": "Check-in and check-out times are not recorded.",
            "ne": "चेक-इन र चेक-आउट समयको जानकारी उपलब्ध छैन।",
        },
    }
    add_message("assistant", questions["introduction"])
    add_message("assistant", questions["dates_and_guests"])

    # Handle missing matched room
    if room is None:
        add_message(
            "hotel",
            replies["missing_room"][language]
        )

        call.transcript = transcript
        call.status = HotelCall.Status.FAILED
        call.failure_reason = "No matched room type is available."
        call.completed_at = timezone.now()

        call.save(update_fields=[
            "transcript",
            "status",
            "failure_reason",
            "completed_at",
            "updated_at",
        ])

        return call

    # Check availability for every night
    stay_dates = [
        requirement.check_in_date + timedelta(days=day)
        for day in range(
            (requirement.check_out_date - requirement.check_in_date).days
        )
    ]

    availability_records = {
        record.date: record
        for record in RoomAvailability.objects.filter(
            room_type=room,
            date__in=stay_dates,
        )
    }

    all_nights_available = all(
        day in availability_records
        and availability_records[day].is_available
        and availability_records[day].available_rooms >= requirement.rooms
        for day in stay_dates
    )

    # Obtain daily prices from stored availability records
    nightly_prices = []

    if all_nights_available:
        for day in stay_dates:
            record = availability_records[day]

            price = (
                record.price_per_night
                if record.price_per_night is not None
                else room.base_price_per_night
            )

            nightly_prices.append(price)

    if not all_nights_available:
        add_message("assistant", questions["availability"])

        add_message(
            "hotel",
            (
                replies["available"][language]
                if all_nights_available
                else replies["unavailable"][language]
            )
        )
    # Determine stored services and facilities
    services = [
        str(item).strip().casefold().replace("_", " ")
        for item in room.included_services
    ]

    room_facilities = list(
        room.facilities.values_list("name", flat=True)
    )

    hotel_facilities = list(
        hotel.hotel_facilities.values_list("facility__name", flat=True)
    )

    all_facilities = {
        str(item).strip().casefold().replace("_", " ")
        for item in services + room_facilities + hotel_facilities
    }

    breakfast = room.breakfast_included

    airport_pickup = (
        True
        if any(
            "airport pickup" in item or "airport transfer" in item
            for item in all_facilities
        )
        else None
    )

    # Simulated conversation questions
    add_message("assistant", questions["price"])

    quoted_price = max(nightly_prices) if nightly_prices else None

    if quoted_price is not None:
        price_reply = (
            f"The price is {quoted_price} {room.currency} "
            "per room per night."
            if language == "en"
            else (
                f"प्रति कोठा प्रति रातको मूल्य "
                f"{quoted_price} {room.currency} हो।"
            )
        )
    else:
        price_reply = replies["price_unknown"][language]

    add_message("hotel", price_reply)

    add_message("assistant", questions["breakfast"])

    add_message(
        "hotel",
        (
            replies["breakfast_yes"][language]
            if breakfast
            else replies["breakfast_no"][language]
        )
    )

    add_message("assistant", questions["airport_pickup"])

    add_message(
        "hotel",
        (
            replies["airport_yes"][language]
            if airport_pickup is True
            else replies["airport_unknown"][language]
        )
    )

       # Read hotel check-in and check-out times safely
    check_in_time = (
        hotel.check_in_time.strftime("%H:%M")
        if hotel.check_in_time
        else None
    )

    check_out_time = (
        hotel.check_out_time.strftime("%H:%M")
        if hotel.check_out_time
        else None
    )

    add_message("assistant", questions["check_in_out"])

    if check_in_time and check_out_time:
        add_message("assistant", questions["check_in_out"])

    if check_in_time and check_out_time:
        time_reply = (
            f"Check-in: {check_in_time}. Check-out: {check_out_time}."
            if language == "en"
            else (
                f"चेक-इन: {check_in_time}। "
                f"चेक-आउट: {check_out_time}।"
            )
        )
    else:
        time_reply = replies["times_unknown"][language]

    add_message("hotel", time_reply)

    # Calculate conservative quoted price per room per night
    quoted_price = max(nightly_prices) if nightly_prices else None

    response_data = {
        "availability": all_nights_available,
        "room_type": room.name,
        "rooms_requested": requirement.rooms,
        "guests": {
            "adults": requirement.adults,
            "children": requirement.children,
        },
        "breakfast_included": breakfast,
        "airport_pickup": airport_pickup,
        "quoted_price_per_room_per_night": (
            str(quoted_price) if quoted_price is not None else None
        ),
        "estimated_total_per_night": (
            str(quoted_price * requirement.rooms)
            if quoted_price is not None else None
        ),
        "currency": room.currency,
        "check_in_time": check_in_time,
        "check_out_time": check_out_time,
        "simulation": True,
    }

    call.transcript = transcript
    call.response_data = response_data
    call.status = HotelCall.Status.COMPLETED
    call.completed_at = timezone.now()
    call.failure_reason = ""

    call.save(update_fields=[
        "transcript",
        "response_data",
        "status",
        "completed_at",
        "failure_reason",
        "updated_at",
    ])

    # Update matching workflow status
    if all_nights_available:
        match.status = HotelMatch.Status.RESPONDED
    else:
        match.status = HotelMatch.Status.UNAVAILABLE

    match.save(update_fields=["status", "updated_at"])

    return call
