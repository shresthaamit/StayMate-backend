
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from hotels.models import Organisation, Membership, Hotel, RoomType, RoomAvailability
from .models import TravellerRequirement, HotelMatch,HotelCall
from .services import generate_hotel_matches

User = get_user_model()


class HotelMatchAPITests(APITestCase):
    def setUp(self):
        # Create a test user
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

        # Create an organisation and owner membership
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

        # Create a verified test hotel
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

        # Create a room
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

        # Create a requirement for the test user
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

        # Create availability for both nights
        for day_offset in range(2):
            RoomAvailability.objects.create(
                room_type=self.room_type,
                date=self.requirement.check_in_date + timedelta(days=day_offset),
                available_rooms=2,
                price_per_night=Decimal("6000.00"),
                is_available=True,
            )

        self.url = f"/api/enquiries/{self.requirement.id}/matches/"

    def test_owner_can_generate_matches(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["requirement_id"], self.requirement.id)
        self.assertEqual(response.data["total_matches"], 1)
        self.assertEqual(
            HotelMatch.objects.filter(requirement=self.requirement).count(),
            1
        )

    def test_repeated_generation_does_not_create_duplicates(self):
        self.client.force_authenticate(user=self.user)

        first_response = self.client.post(self.url, {}, format="json")
        second_response = self.client.post(self.url, {}, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HotelMatch.objects.filter(requirement=self.requirement).count(),
            1
        )

    def test_another_user_cannot_generate_matches(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_user_cannot_generate_matches(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    def test_stale_shortlisted_match_is_deleted(self):
        # Generate an initial match
        generate_hotel_matches(self.requirement)

        self.assertTrue(
            HotelMatch.objects.filter(
                requirement=self.requirement,
                hotel=self.hotel,
                status=HotelMatch.Status.SHORTLISTED
            ).exists()
        )

        # Make the hotel ineligible
        self.hotel.status = "inactive"
        self.hotel.save(update_fields=["status"])

        # Generate matches again
        generate_hotel_matches(self.requirement)

        # The stale shortlisted match should be deleted
        self.assertFalse(
            HotelMatch.objects.filter(
                requirement=self.requirement,
                hotel=self.hotel
            ).exists()
        )


    def test_stale_call_pending_match_is_preserved(self):
        # Create a match that has progressed in the calling workflow
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

        # Make the hotel ineligible
        self.hotel.status = "inactive"
        self.hotel.save(update_fields=["status"])

        # Generate matches again
        generate_hotel_matches(self.requirement)

        # The progressed match must remain unchanged
        existing_match.refresh_from_db()

        self.assertEqual(
            existing_match.status,
            HotelMatch.Status.CALL_PENDING
        )

        self.assertTrue(
            HotelMatch.objects.filter(pk=existing_match.pk).exists()
        )

    def test_stale_shortlisted_match_is_deleted(self):
        # Generate an initial match
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Make the hotel ineligible
        self.hotel.status = "inactive"
        self.hotel.save()

        # Generate matches again
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The stale shortlisted match should be deleted
        self.assertFalse(
            HotelMatch.objects.filter(
                requirement=self.requirement,
                hotel=self.hotel
            ).exists()
        )

    def test_stale_call_pending_match_is_preserved(self):
        # Create a match that has progressed beyond shortlisting
        existing_match = HotelMatch.objects.create(
            requirement=self.requirement,
            hotel=self.hotel,
            matched_room_type=self.room_type,
            match_score=67,
            match_reasons=["Test match"],
            estimated_price_per_night=Decimal("6000.00"),
            currency="NPR",
            status=HotelMatch.Status.CALL_PENDING,
        )

        # Make the hotel ineligible
        self.hotel.status = "inactive"
        self.hotel.save()

        # Generate matches again
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The progressed match must remain unchanged
        existing_match.refresh_from_db()
        self.assertEqual(
            existing_match.status,
            HotelMatch.Status.CALL_PENDING
        )
        self.assertTrue(
            HotelMatch.objects.filter(pk=existing_match.pk).exists()
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
                date=self.requirement.check_in_date + timedelta(days=day_offset),
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

    def test_missing_room_type_fails_call(self):
        self.match.matched_room_type = None
        self.match.save(update_fields=["matched_room_type"])

        call_id = self.create_call()

        response = self.client.post(
            f"/api/enquiries/calls/{call_id}/simulate/",
            {},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

        # Create a second attempt after the first has failed
        second_call_id = self.create_call()

        second_call = HotelCall.objects.get(pk=second_call_id)

        self.assertEqual(second_call.attempt_number, 2)
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
