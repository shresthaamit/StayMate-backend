
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from .services import resolve_hotel_contact
from hotels.models import (
    Organisation,
    Membership,
    Hotel,
    HotelContact,
    RoomType,
    RoomAvailability,
)
from enquiries.calling.conversation import HotelConversationEngine
from .models import TravellerRequirement, HotelMatch, HotelCall


User = get_user_model()


class HotelMatchAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testowner",
            email="testowner@example.com",
            password="TestPassword123!"
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            email="otheruser@example.com",
            password="TestPassword123!"
        )

        self.organisation = Organisation.objects.create(
            name="Test Organisation",
            created_by=self.user,
            status="active"
        )

        Membership.objects.create(
            organisation=self.organisation,
            user=self.user,
            role="owner",
            is_active=True
        )

        self.hotel = Hotel.objects.create(
            organisation=self.organisation,
            name="Automated Test Hotel",
            hotel_type="hotel",
            star_rating=3,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            address="Test address, Pokhara, Nepal",
            contact_phone="+9779800000000",
            status="active",
            is_verified=True,
        )

        self.room_type = RoomType.objects.create(
            hotel=self.hotel,
            name="Test Double Room",
            max_occupancy=2,
            adult_capacity=2,
            child_capacity=0,
            total_rooms=2,
            bed_type="double",
            number_of_beds=1,
            base_price_per_night=Decimal("6000.00"),
            currency="NPR",
            breakfast_included=True,
            included_services=["breakfast"],
            is_active=True,
        )

        self.requirement = TravellerRequirement.objects.create(
            user=self.user,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=12),
            adults=2,
            children=0,
            rooms=1,
            max_budget_per_night=Decimal("8000.00"),
            currency="NPR",
            preferred_hotel_types=["hotel"],
            required_facilities=["breakfast"],
        )

        for day_offset in range(2):
            RoomAvailability.objects.create(
                room_type=self.room_type,
                date=self.requirement.check_in_date
                + timedelta(days=day_offset),
                available_rooms=2,
                price_per_night=Decimal("6000.00"),
                is_available=True,
            )

        self.url = (
            f"/api/enquiries/{self.requirement.id}/matches/"
        )

    def test_owner_can_generate_matches(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["requirement_id"],
            self.requirement.id
        )
        self.assertEqual(response.data["total_matches"], 1)

        self.assertEqual(
            HotelMatch.objects.filter(
                requirement=self.requirement
            ).count(),
            1
        )

    def test_repeated_generation_does_not_create_duplicates(self):
        self.client.force_authenticate(user=self.user)

        first_response = self.client.post(
            self.url,
            {},
            format="json"
        )

        second_response = self.client.post(
            self.url,
            {},
            format="json"
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            HotelMatch.objects.filter(
                requirement=self.requirement
            ).count(),
            1
        )

    def test_another_user_cannot_generate_matches(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            self.url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )

    def test_unauthenticated_user_cannot_generate_matches(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_stale_shortlisted_match_is_deleted(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertTrue(
            HotelMatch.objects.filter(
                requirement=self.requirement,
                hotel=self.hotel,
                status=HotelMatch.Status.SHORTLISTED
            ).exists()
        )

        self.hotel.status = "inactive"
        self.hotel.save()

        response = self.client.post(
            self.url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertFalse(
            HotelMatch.objects.filter(
                requirement=self.requirement,
                hotel=self.hotel
            ).exists()
        )

    def test_stale_call_pending_match_is_preserved(self):
        existing_match = HotelMatch.objects.create(
            requirement=self.requirement,
            hotel=self.hotel,
            matched_room_type=self.room_type,
            match_score=67,
            match_reasons=["Test match"],
            estimated_price_per_night=Decimal("6000.00"),
            currency="NPR",
            status=HotelMatch.Status.CALL_PENDING
        )

        self.hotel.status = "inactive"
        self.hotel.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        existing_match.refresh_from_db()

        self.assertEqual(
            existing_match.status,
            HotelMatch.Status.CALL_PENDING
        )

        self.assertTrue(
            HotelMatch.objects.filter(
                pk=existing_match.pk
            ).exists()
        )


class HotelCallAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="callowner",
            email="callowner@example.com",
            password="TestPassword123!"
        )

        self.organisation = Organisation.objects.create(
            name="Call Test Organisation",
            created_by=self.user,
            status="active"
        )

        Membership.objects.create(
            organisation=self.organisation,
            user=self.user,
            role="owner",
            is_active=True
        )

        self.hotel = Hotel.objects.create(
            organisation=self.organisation,
            name="Call Test Hotel",
            hotel_type="hotel",
            star_rating=3,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            address="Test address, Pokhara, Nepal",
            contact_phone="+9779800000000",
            status="active",
            is_verified=True,
        )

        self.room_type = RoomType.objects.create(
            hotel=self.hotel,
            name="Call Test Double Room",
            max_occupancy=2,
            adult_capacity=2,
            child_capacity=0,
            total_rooms=2,
            bed_type="double",
            number_of_beds=1,
            base_price_per_night=Decimal("6000.00"),
            currency="NPR",
            breakfast_included=True,
            included_services=["breakfast", "airport_pickup"],
            is_active=True,
        )

        self.requirement = TravellerRequirement.objects.create(
            user=self.user,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=12),
            adults=2,
            children=0,
            rooms=1,
            max_budget_per_night=Decimal("8000.00"),
            currency="NPR",
            preferred_hotel_types=["hotel"],
            required_facilities=["breakfast"],
        )

        for day_offset in range(2):
            RoomAvailability.objects.create(
                room_type=self.room_type,
                date=self.requirement.check_in_date
                + timedelta(days=day_offset),
                available_rooms=2,
                price_per_night=Decimal("6000.00"),
                is_available=True,
            )

        self.match = HotelMatch.objects.create(
            requirement=self.requirement,
            hotel=self.hotel,
            matched_room_type=self.room_type,
            match_score=80,
            match_reasons=["Test match"],
            estimated_price_per_night=Decimal("6000.00"),
            currency="NPR",
            status=HotelMatch.Status.SHORTLISTED,
        )

        self.client.force_authenticate(user=self.user)

        self.calls_url = (
            f"/api/enquiries/matches/{self.match.id}/calls/"
        )

    def create_call(self):
        response = self.client.post(
            self.calls_url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        return response.data["id"]

    def test_queued_call_can_be_simulated(self):
        call_id = self.create_call()

        response = self.client.post(
            f"/api/enquiries/calls/{call_id}/simulate/",
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["status"],
            HotelCall.Status.COMPLETED
        )

        self.assertGreater(
            len(response.data["transcript"]),
            0
        )

        self.assertTrue(
            response.data["response_data"]["availability"]
        )

        self.assertEqual(
            response.data["response_data"][
                "quoted_price_per_room_per_night"
            ],
            "6000.00"
        )

        self.match.refresh_from_db()

        self.assertEqual(
            self.match.status,
            HotelMatch.Status.RESPONDED
        )

    def test_unavailable_room_is_recorded(self):
        RoomAvailability.objects.filter(
            room_type=self.room_type,
            date=self.requirement.check_in_date + timedelta(days=1)
        ).update(is_available=False)

        call_id = self.create_call()

        response = self.client.post(
            f"/api/enquiries/calls/{call_id}/simulate/",
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["status"],
            HotelCall.Status.COMPLETED
        )

        self.assertFalse(
            response.data["response_data"]["availability"]
        )

        self.match.refresh_from_db()

        self.assertEqual(
            self.match.status,
            HotelMatch.Status.UNAVAILABLE
        )

    def test_conversation_engine_generates_english_questions(self):
        self.call = HotelCall.objects.create(
            hotel_match=self.match,
            attempt_number=1,
            target_language="en",
        )

        engine = HotelConversationEngine(self.call)
        questions = engine.build_questions()

        keys = [item["key"] for item in questions]

        self.assertEqual(
            keys,
            [
                "introduction",
                "dates_and_guests",
                "availability",
                "price",
                "breakfast",
                "airport_pickup",
                "check_in_out",
            ],
        )

        self.assertIn("StayMate", questions[0]["message"])
        self.assertIn("adults", questions[1]["message"])

    def test_conversation_engine_generates_nepali_questions(self):
        self.call = HotelCall.objects.create(
            hotel_match=self.match,
            attempt_number=1,
            target_language="ne",
        )

        engine = HotelConversationEngine(self.call)
        questions = engine.build_questions()

        self.assertEqual(len(questions), 7)
        self.assertIn("नमस्कार", questions[0]["message"])
        self.assertIn("विमानस्थल", questions[5]["message"])

    def test_conversation_engine_defaults_unsupported_language_to_english(self):
        self.call = HotelCall.objects.create(
            hotel_match=self.match,
            attempt_number=1,
            target_language="fr",
        )

        engine = HotelConversationEngine(self.call)
        questions = engine.build_questions()

        self.assertEqual(engine.language, "en")
        self.assertIn("Hello", questions[0]["message"])
    def test_primary_reservation_contact_is_selected(self):
        receptionist = HotelContact.objects.create(
            hotel=self.hotel,
            name="Receptionist",
            role=HotelContact.ContactRole.RECEPTIONIST,
            phone_number="+9779800000001",
        )

        reservation = HotelContact.objects.create(
            hotel=self.hotel,
            name="Reservation Manager",
            role=HotelContact.ContactRole.RESERVATION,
            phone_number="+9779800000002",
            is_primary=True,
            preferred_language="Nepali",
        )

        result = resolve_hotel_contact(self.hotel)

        self.assertTrue(result["available"])
        self.assertEqual(result["contact_id"], reservation.id)
        self.assertEqual(result["contact_name"], "Reservation Manager")
        self.assertEqual(result["phone_number"], "+9779800000002")
        self.assertEqual(result["language"], "ne")
        self.assertEqual(result["source"], "hotel_contact")

    def test_reservation_contact_has_priority_over_receptionist(self):
        receptionist = HotelContact.objects.create(
            hotel=self.hotel,
            name="Primary Receptionist",
            role=HotelContact.ContactRole.RECEPTIONIST,
            phone_number="+9779800000001",
            is_primary=True,
        )

        reservation = HotelContact.objects.create(
            hotel=self.hotel,
            name="Reservation Staff",
            role=HotelContact.ContactRole.RESERVATION,
            phone_number="+9779800000002",
        )

        result = resolve_hotel_contact(self.hotel)

        self.assertEqual(result["contact_id"], reservation.id)

    def test_hotel_alternative_phone_is_used_when_no_contacts_exist(self):
        self.hotel.alternative_phone = "+9779800000003"
        self.hotel.preferred_language = "Nepali"
        self.hotel.save()

        result = resolve_hotel_contact(self.hotel)

        self.assertTrue(result["available"])
        self.assertEqual(
            result["phone_number"],
            "+9779800000003"
        )
        self.assertEqual(result["language"], "ne")
        self.assertEqual(
            result["source"],
            "hotel_alternative_phone"
        )

    def test_main_phone_is_used_when_alternative_is_missing(self):
        self.hotel.alternative_phone = ""
        self.hotel.save()

        result = resolve_hotel_contact(self.hotel)

        self.assertTrue(result["available"])
        self.assertEqual(
            result["phone_number"],
            self.hotel.contact_phone
        )
        self.assertEqual(
            result["source"],
            "hotel_main_phone"
        )

    def test_contact_language_falls_back_to_hotel_language(self):
        self.hotel.preferred_language = "Nepali"
        self.hotel.save()

        contact = HotelContact.objects.create(
            hotel=self.hotel,
            name="Receptionist",
            role=HotelContact.ContactRole.RECEPTIONIST,
            phone_number="+9779800000004",
            preferred_language="",
        )

        result = resolve_hotel_contact(self.hotel)

        self.assertEqual(result["contact_id"], contact.id)
        self.assertEqual(result["language"], "ne")

    def test_no_available_phone_returns_unavailable(self):
        self.hotel.contact_phone = ""
        self.hotel.alternative_phone = ""
        self.hotel.save()

        result = resolve_hotel_contact(self.hotel)

        self.assertFalse(result["available"])
        self.assertIsNone(result["phone_number"])

    def test_missing_room_type_fails_call(self):
        self.match.matched_room_type = None
        self.match.save(update_fields=["matched_room_type"])

        call_id = self.create_call()

        response = self.client.post(
            f"/api/enquiries/calls/{call_id}/simulate/",
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["status"],
            HotelCall.Status.FAILED
        )

        self.assertEqual(
            response.data["failure_reason"],
            "No matched room type is available."
        )

    def test_completed_call_cannot_be_simulated_twice(self):
        call_id = self.create_call()

        first_response = self.client.post(
            f"/api/enquiries/calls/{call_id}/simulate/",
            {},
            format="json"
        )

        second_response = self.client.post(
            f"/api/enquiries/calls/{call_id}/simulate/",
            {},
            format="json"
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_failed_call_can_be_retried(self):
        self.match.matched_room_type = None
        self.match.save(update_fields=["matched_room_type"])

        first_call_id = self.create_call()

        first_response = self.client.post(
            f"/api/enquiries/calls/{first_call_id}/simulate/",
            {},
            format="json"
        )

        self.assertEqual(
            first_response.data["status"],
            HotelCall.Status.FAILED
        )

        second_call_id = self.create_call()

        second_call = HotelCall.objects.get(
            pk=second_call_id
        )

        self.assertEqual(
            second_call.attempt_number,
            2
        )

        self.assertEqual(
            second_call.status,
            HotelCall.Status.QUEUED
        )

        self.assertEqual(
            HotelCall.objects.filter(
                hotel_match=self.match
            ).count(),
            2
        )
    def test_call_creation_saves_primary_reservation_contact_snapshot(self):
        # A primary receptionist should not outrank a reservation contact.
        HotelContact.objects.create(
            hotel=self.hotel,
            name="Primary Receptionist",
            role=HotelContact.ContactRole.RECEPTIONIST,
            phone_number="+9779800000001",
            is_primary=True,
        )

        reservation = HotelContact.objects.create(
            hotel=self.hotel,
            name="Reservation Manager",
            role=HotelContact.ContactRole.RESERVATION,
            phone_number="+9779800000002",
            is_primary=False,
            preferred_language="Nepali",
        )

        response = self.client.post(
            self.calls_url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        call = HotelCall.objects.get(pk=response.data["id"])

        self.assertEqual(call.target_contact_id, reservation.id)
        self.assertEqual(
            call.target_contact_name,
            "Reservation Manager"
        )
        self.assertEqual(
            call.target_contact_role,
            HotelContact.ContactRole.RESERVATION
        )
        self.assertEqual(
            call.target_phone_number,
            "+9779800000002"
        )
        self.assertEqual(call.target_language, "ne")
        self.assertEqual(
            call.target_contact_source,
            "hotel_contact"
        )

        # Verify the API response also exposes the saved snapshot.
        self.assertEqual(
            response.data["target_phone_number"],
            "+9779800000002"
        )
        self.assertEqual(response.data["target_language"], "ne")

    def test_call_creation_uses_alternative_phone_when_no_contacts_exist(self):
        self.hotel.alternative_phone = "+9779800000003"
        self.hotel.preferred_language = "Nepali"
        self.hotel.save()

        response = self.client.post(
            self.calls_url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        call = HotelCall.objects.get(pk=response.data["id"])

        self.assertEqual(
            call.target_phone_number,
            "+9779800000003"
        )
        self.assertEqual(call.target_language, "ne")
        self.assertEqual(
            call.target_contact_source,
            "hotel_alternative_phone"
        )
        self.assertIsNone(call.target_contact_id)

    def test_call_creation_uses_main_phone_when_alternative_is_missing(self):
        self.hotel.alternative_phone = ""
        self.hotel.save()

        response = self.client.post(
            self.calls_url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        call = HotelCall.objects.get(pk=response.data["id"])

        self.assertEqual(
            call.target_phone_number,
            self.hotel.contact_phone
        )
        self.assertEqual(
            call.target_contact_source,
            "hotel_main_phone"
        )

    def test_call_creation_fails_when_no_phone_number_is_available(self):
        self.hotel.contact_phone = ""
        self.hotel.alternative_phone = ""
        self.hotel.save()

        response = self.client.post(
            self.calls_url,
            {},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(
            HotelCall.objects.filter(
                hotel_match=self.match
            ).count(),
            0
        )

        self.match.refresh_from_db()

        self.assertEqual(
            self.match.status,
            HotelMatch.Status.SHORTLISTED
        )


class TravellerResultsAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="resultsowner",
            email="resultsowner@example.com",
            password="TestPassword123!"
        )

        self.other_user = User.objects.create_user(
            username="resultsother",
            email="resultsother@example.com",
            password="TestPassword123!"
        )

        self.organisation = Organisation.objects.create(
            name="Results Test Organisation",
            created_by=self.user,
            status="active"
        )

        Membership.objects.create(
            organisation=self.organisation,
            user=self.user,
            role="owner",
            is_active=True
        )

        self.hotel = Hotel.objects.create(
            organisation=self.organisation,
            name="Results Test Hotel",
            hotel_type="hotel",
            star_rating=3,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            address="Results test address, Pokhara, Nepal",
            contact_phone="+9779800000000",
            status="active",
            is_verified=True,
        )

        self.room_type = RoomType.objects.create(
            hotel=self.hotel,
            name="Results Test Double Room",
            max_occupancy=2,
            adult_capacity=2,
            child_capacity=0,
            total_rooms=2,
            bed_type="double",
            number_of_beds=1,
            base_price_per_night=Decimal("6000.00"),
            currency="NPR",
            breakfast_included=True,
            included_services=["breakfast"],
            is_active=True,
        )

        self.requirement = TravellerRequirement.objects.create(
            user=self.user,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=12),
            adults=2,
            children=0,
            rooms=1,
            max_budget_per_night=Decimal("8000.00"),
            currency="NPR",
            preferred_hotel_types=["hotel"],
            required_facilities=["breakfast"],
        )

        self.match = HotelMatch.objects.create(
            requirement=self.requirement,
            hotel=self.hotel,
            matched_room_type=self.room_type,
            match_score=80,
            match_reasons=[
                "Within budget",
                "Breakfast included"
            ],
            estimated_price_per_night=Decimal("6000.00"),
            currency="NPR",
            status=HotelMatch.Status.RESPONDED,
        )

        self.url = (
            f"/api/enquiries/{self.requirement.id}/results/"
        )

        self.client.force_authenticate(user=self.user)

    def create_comparison_match(self, name="Comparison Test Hotel"):
        hotel = Hotel.objects.create(
            organisation=self.organisation,
            name=name,
            hotel_type="resort",
            star_rating=4,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            address="Comparison test address, Pokhara, Nepal",
            contact_phone="+9779800000001",
            status="active",
            is_verified=True,
        )

        room = RoomType.objects.create(
            hotel=hotel,
            name="Comparison Test Room",
            max_occupancy=2,
            adult_capacity=2,
            child_capacity=0,
            total_rooms=2,
            bed_type="double",
            number_of_beds=1,
            base_price_per_night=Decimal("4500.00"),
            currency="NPR",
            breakfast_included=False,
            included_services=[],
            is_active=True,
        )

        return HotelMatch.objects.create(
            requirement=self.requirement,
            hotel=hotel,
            matched_room_type=room,
            match_score=90,
            match_reasons=["Comparison test match"],
            estimated_price_per_night=Decimal("4500.00"),
            currency="NPR",
            status=HotelMatch.Status.RESPONDED,
        )
    def test_owner_can_compare_two_hotels(self):
        second_match = self.create_comparison_match()

        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {"match_ids": f"{self.match.id},{second_match.id}"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_compared"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_comparison_preserves_selected_order(self):
        second_match = self.create_comparison_match()

        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {"match_ids": f"{second_match.id},{self.match.id}"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [second_match.id, self.match.id]
        )

    def test_comparison_requires_at_least_two_matches(self):
        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {"match_ids": str(self.match.id)}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comparison_allows_maximum_four_matches(self):
        second = self.create_comparison_match("Comparison Hotel 2")
        third = self.create_comparison_match("Comparison Hotel 3")
        fourth = self.create_comparison_match("Comparison Hotel 4")

        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {
                "match_ids": (
                    f"{self.match.id},{second.id},"
                    f"{third.id},{fourth.id}"
                )
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_compared"], 4)

    def test_comparison_rejects_more_than_four_matches(self):
        second = self.create_comparison_match("Comparison Hotel 2")
        third = self.create_comparison_match("Comparison Hotel 3")
        fourth = self.create_comparison_match("Comparison Hotel 4")
        fifth = self.create_comparison_match("Comparison Hotel 5")

        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {
                "match_ids": (
                    f"{self.match.id},{second.id},"
                    f"{third.id},{fourth.id},{fifth.id}"
                )
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comparison_rejects_duplicate_ids(self):
        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {"match_ids": f"{self.match.id},{self.match.id}"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comparison_rejects_invalid_ids(self):
        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {"match_ids": "abc,xyz"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comparison_rejects_match_from_another_requirement(self):
        other_requirement = TravellerRequirement.objects.create(
            user=self.other_user,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=12),
            adults=2,
            children=0,
            rooms=1,
            max_budget_per_night=Decimal("8000.00"),
            currency="NPR",
            preferred_hotel_types=["hotel"],
            required_facilities=["breakfast"],
        )

        other_match = HotelMatch.objects.create(
            requirement=other_requirement,
            hotel=self.hotel,
            matched_room_type=self.room_type,
            match_score=70,
            match_reasons=["Other requirement test"],
            estimated_price_per_night=Decimal("6000.00"),
            currency="NPR",
            status=HotelMatch.Status.RESPONDED,
        )

        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {"match_ids": f"{self.match.id},{other_match.id}"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_another_user_cannot_compare_requirement(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {"match_ids": str(self.match.id) + ",999"}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_user_cannot_compare_hotels(self):
        self.client.force_authenticate(user=None)

        second_match = self.create_comparison_match()

        response = self.client.get(
            f"/api/enquiries/{self.requirement.id}/compare/",
            {"match_ids": f"{self.match.id},{second_match.id}"}
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )
    def create_additional_match(
        self,
        name="Second Results Hotel",
        hotel_type="resort",
        star_rating=4,
        price="4000.00",
        match_score=90,
        breakfast_included=False,
    ):
        hotel = Hotel.objects.create(
            organisation=self.organisation,
            name=name,
            hotel_type=hotel_type,
            star_rating=star_rating,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            address="Second test address, Pokhara, Nepal",
            contact_phone="+9779800000001",
            status="active",
            is_verified=True,
        )

        room = RoomType.objects.create(
            hotel=hotel,
            name="Second Test Room",
            max_occupancy=2,
            adult_capacity=2,
            child_capacity=0,
            total_rooms=2,
            bed_type="double",
            number_of_beds=1,
            base_price_per_night=Decimal(price),
            currency="NPR",
            breakfast_included=breakfast_included,
            included_services=[],
            is_active=True,
        )

        return HotelMatch.objects.create(
            requirement=self.requirement,
            hotel=hotel,
            matched_room_type=room,
            match_score=match_score,
            match_reasons=["Additional test match"],
            estimated_price_per_night=Decimal(price),
            currency="NPR",
            status=HotelMatch.Status.RESPONDED,
        )


    def test_filter_by_minimum_price(self):
        response = self.client.get(
            self.url,
            {"min_price": "5000"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 1)

    def test_filter_by_maximum_price(self):
        response = self.client.get(
            self.url,
            {"max_price": "5000"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 0)

    def test_filter_by_price_range(self):
        self.create_additional_match(price="4000.00")

        response = self.client.get(
            self.url,
            {
                "min_price": "3000",
                "max_price": "5000",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 1)
        self.assertEqual(
            response.data["results"][0]["estimated_price_per_night"],
            "4000.00"
        )

    def test_filter_by_minimum_star_rating(self):
        response = self.client.get(
            self.url,
            {"min_star_rating": "4"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 0)

    def test_filter_by_hotel_type(self):
        response = self.client.get(
            self.url,
            {"hotel_type": "HOTEL"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 1)

    def test_filter_by_breakfast_included(self):
        response = self.client.get(
            self.url,
            {"breakfast_included": "true"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 1)

    def test_filter_by_airport_pickup_true(self):
        HotelCall.objects.create(
            hotel_match=self.match,
            attempt_number=1,
            response_data={"airport_pickup": True},
        )

        response = self.client.get(
            self.url,
            {"airport_pickup": "true"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 1)

    def test_filter_by_airport_pickup_false(self):
        HotelCall.objects.create(
            hotel_match=self.match,
            attempt_number=1,
            response_data={"airport_pickup": False},
        )

        response = self.client.get(
            self.url,
            {"airport_pickup": "false"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 1)

    def test_unknown_airport_pickup_does_not_match_false(self):
        HotelCall.objects.create(
            hotel_match=self.match,
            attempt_number=1,
            response_data={},
        )

        response = self.client.get(
            self.url,
            {"airport_pickup": "false"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_matches"], 0)

    
    def test_sort_by_price_ascending(self):
        self.create_additional_match(price="4000.00")

        response = self.client.get(
            self.url,
            {"sort_by": "price", "order": "asc"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        prices = [
            Decimal(item["estimated_price_per_night"])
            for item in response.data["results"]
        ]

        self.assertEqual(prices, [Decimal("4000.00"), Decimal("6000.00")])

    def test_sort_by_match_score_descending(self):
        self.create_additional_match(
            price="4000.00",
            match_score=90,
        )

        response = self.client.get(
            self.url,
            {"sort_by": "match_score", "order": "desc"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        scores = [
            item["match_score"]
            for item in response.data["results"]
        ]

        self.assertEqual(scores, [90, 80])

    def test_sort_by_star_rating_descending(self):
        self.create_additional_match(
            price="4000.00",
            star_rating=4,
        )

        response = self.client.get(
            self.url,
            {"sort_by": "star_rating", "order": "desc"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ratings = [
            item["hotel"]["star_rating"]
            for item in response.data["results"]
        ]

        self.assertEqual(ratings, [4, 3])

    def test_invalid_sort_field_returns_bad_request(self):
        response = self.client.get(
            self.url,
            {"sort_by": "invalid"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_price_returns_bad_request(self):
        response = self.client.get(
            self.url,
            {"min_price": "abc"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_minimum_price_cannot_exceed_maximum_price(self):
        response = self.client.get(
            self.url,
            {
                "min_price": "9000",
                "max_price": "3000",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_boolean_filter_returns_bad_request(self):
        response = self.client.get(
            self.url,
            {"breakfast_included": "yes"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_requires_sort_field(self):
        response = self.client.get(
            self.url,
            {"order": "asc"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_owner_can_retrieve_results(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["requirement_id"],
            self.requirement.id
        )

        self.assertEqual(
            response.data["total_matches"],
            1
        )

        self.assertEqual(
            len(response.data["results"]),
            1
        )

        self.assertEqual(
            response.data["results"][0]["hotel"]["name"],
            self.hotel.name
        )

    def test_results_can_be_empty(self):
        self.match.delete()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data["total_matches"],
            0
        )

        self.assertEqual(
            response.data["results"],
            []
        )

    def test_another_user_cannot_access_results(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )

    def test_unauthenticated_user_cannot_access_results(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_results_include_latest_call_attempt(self):
        first_call = HotelCall.objects.create(
            hotel_match=self.match,
            attempt_number=1,
        )

        second_call = HotelCall.objects.create(
            hotel_match=self.match,
            attempt_number=2,
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        returned_call = response.data["results"][0]["latest_call"]

        latest_call = HotelCall.objects.filter(
            hotel_match=self.match
        ).order_by("-created_at", "-id").first()

        self.assertEqual(
            returned_call["id"],
            latest_call.id
        )

        self.assertEqual(
            returned_call["attempt_number"],
            2
        )

        self.assertNotEqual(
            returned_call["id"],
            first_call.id
        )

        self.assertEqual(
            second_call.attempt_number,
            2
        )
