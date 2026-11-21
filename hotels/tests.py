
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Organisation, Hotel


class NearbyHotelAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.url = "/api/hotels/nearby/"

        self.latitude = "28.2096"
        self.longitude = "83.9856"

        self.organisation = Organisation.objects.create(
            name="Nearby Test Organisation",
            status=Organisation.Status.ACTIVE,
        )

        self.nearby_hotel = self.create_hotel(
            name="Nearby Verified Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("83.9856"),
        )

    def create_hotel(
        self,
        name,
        latitude=None,
        longitude=None,
        is_verified=True,
        status=Hotel.Status.ACTIVE,
        organisation=None,
        is_deleted=False,
    ):
        return Hotel.objects.create(
            organisation=organisation or self.organisation,
            name=name,
            country="Nepal",
            province="Gandaki",
            city="Pokhara",
            area="Lakeside",
            address="Test address, Pokhara",
            contact_phone="+9779800000000",
            latitude=latitude,
            longitude=longitude,
            is_verified=is_verified,
            status=status,
            is_deleted=is_deleted,
        )

    def search(self, **params):
        default_params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius_km": "10",
        }
        default_params.update(params)

        return self.client.get(self.url, default_params)

    def test_returns_nearby_verified_hotel(self):
        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["name"],
            "Nearby Verified Hotel",
        )
        self.assertEqual(
            response.data["results"][0]["distance_km"],
            0.0,
        )

    def test_excludes_hotel_outside_radius(self):
        self.create_hotel(
            name="Far Away Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("84.2000"),
        )

        response = self.search(radius_km="5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn("Far Away Hotel", hotel_names)

    def test_excludes_unverified_hotel(self):
        self.create_hotel(
            name="Unverified Hotel",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
            is_verified=False,
        )

        response = self.search()

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn("Unverified Hotel", hotel_names)

    def test_excludes_hotel_without_coordinates(self):
        self.create_hotel(
            name="Hotel Without Coordinates",
            latitude=None,
            longitude=None,
        )

        response = self.search()

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn(
            "Hotel Without Coordinates",
            hotel_names,
        )

    def test_excludes_hotel_with_inactive_organisation(self):
        inactive_organisation = Organisation.objects.create(
            name="Inactive Test Organisation",
            status=Organisation.Status.INACTIVE,
        )

        self.create_hotel(
            name="Inactive Organisation Hotel",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
            organisation=inactive_organisation,
        )

        response = self.search()

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn(
            "Inactive Organisation Hotel",
            hotel_names,
        )

    def test_missing_latitude_returns_400(self):
        response = self.client.get(
            self.url,
            {
                "longitude": self.longitude,
                "radius_km": "10",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_latitude_returns_400(self):
        response = self.search(latitude="100")

        self.assertEqual(response.status_code, 400)

    def test_invalid_longitude_returns_400(self):
        response = self.search(longitude="200")

        self.assertEqual(response.status_code, 400)

    def test_invalid_radius_returns_400(self):
        response = self.search(radius_km="0")

        self.assertEqual(response.status_code, 400)

    def test_radius_above_maximum_returns_400(self):
        response = self.search(radius_km="150")

        self.assertEqual(response.status_code, 400)

    def test_invalid_coordinate_text_returns_400(self):
        response = self.search(latitude="invalid")

        self.assertEqual(response.status_code, 400)

    
    def test_filters_by_city(self):
        response = self.search(city="Pokhara")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filters_by_area(self):
        response = self.search(area="Lakeside")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filters_by_minimum_star_rating(self):
        response = self.search(min_star_rating="4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_filters_by_hotel_type(self):
        response = self.search(hotel_type="hotel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_rejects_invalid_hotel_type(self):
        response = self.search(hotel_type="palace")

        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_star_rating(self):
        response = self.search(min_star_rating="6")

        self.assertEqual(response.status_code, 400)

    def test_rejects_minimum_rating_above_maximum(self):
        response = self.search(
            min_star_rating="5",
            max_star_rating="3",
        )

        self.assertEqual(response.status_code, 400)


    def test_default_sorting_is_ascending(self):
        self.create_hotel(
            name="Farther Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("84.0000"),
        )

        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["sort_order"],
            "asc",
        )
        self.assertEqual(
            response.data["results"][0]["name"],
            "Nearby Verified Hotel",
        )

    def test_explicit_ascending_sorting(self):
        self.create_hotel(
            name="Farther Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("84.0000"),
        )

        response = self.search(sort_order="asc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["results"][0]["name"],
            "Nearby Verified Hotel",
        )

    def test_descending_sorting(self):
        self.create_hotel(
            name="Farther Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("84.0000"),
        )

        response = self.search(sort_order="desc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["sort_order"],
            "desc",
        )
        self.assertEqual(
            response.data["results"][0]["name"],
            "Farther Hotel",
        )

    def test_invalid_sort_order_returns_400(self):
        response = self.search(sort_order="random")

        self.assertEqual(response.status_code, 400)

    def test_response_includes_search_location(self):
        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["search_location"],
            {
                "latitude": 28.2096,
                "longitude": 83.9856,
            },
        )

    def test_response_includes_radius_and_sort_order(self):
        response = self.search(radius_km="10", sort_order="asc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["radius_km"], 10.0)
        self.assertEqual(response.data["sort_order"], "asc")
