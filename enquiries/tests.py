
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from hotels.models import Organisation, Membership, Hotel, RoomType, RoomAvailability
from .models import TravellerRequirement, HotelMatch


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
