from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Organisation, Hotel, HotelFacility,Facility


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


    def destination_search(self, **params):
        return self.client.get(
            "/api/hotels/search/",
            params
        )


    def test_destination_search_by_city(self):
        response = self.destination_search(city="Pokhara")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["name"],
            "Nearby Verified Hotel",
        )

    def test_destination_search_by_area(self):
        response = self.destination_search(area="Lakeside")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_destination_search_by_city_and_area(self):
        response = self.destination_search(
            city="Pokhara",
            area="Lakeside",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_destination_search_does_not_require_coordinates(self):
        self.create_hotel(
            name="Hotel Without GPS",
            latitude=None,
            longitude=None,
        )

        response = self.destination_search(city="Pokhara")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_destination_search_requires_city_or_area(self):
        response = self.destination_search()

        self.assertEqual(response.status_code, 400)

    def test_destination_search_excludes_unverified_hotels(self):
        self.create_hotel(
            name="Unverified Destination Hotel",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
            is_verified=False,
        )

        response = self.destination_search(city="Pokhara")

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn(
            "Unverified Destination Hotel",
            hotel_names,
        )
    # -------------------------
    # Pagination tests
    # -------------------------

    def test_destination_search_paginates_first_page(self):
        self.create_hotel(
            name="Alpha Hotel",
        )
        self.create_hotel(
            name="Bravo Hotel",
        )

        response = self.destination_search(
            city="Pokhara",
            page="1",
            page_size="2",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)

        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

        self.assertEqual(
            response.data["search_destination"]["city"],
            "Pokhara",
        )

        # These two hotels have no coordinates.
        self.assertEqual(response.data["map_markers"], [])

    def test_destination_search_paginates_second_page(self):
        self.create_hotel(
            name="Alpha Hotel",
        )
        self.create_hotel(
            name="Bravo Hotel",
        )

        response = self.destination_search(
            city="Pokhara",
            page="2",
            page_size="2",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 1)

        self.assertIsNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

        self.assertEqual(
            response.data["results"][0]["name"],
            "Nearby Verified Hotel",
        )

        # The remaining hotel has coordinates, so it gets a map marker.
        self.assertEqual(len(response.data["map_markers"]), 1)
        self.assertEqual(
            response.data["map_markers"][0]["id"],
            self.nearby_hotel.id,
        )

    def test_nearby_search_paginates_and_preserves_metadata(self):
        self.create_hotel(
            name="Farther Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("83.9900"),
        )

        self.create_hotel(
            name="Farthest Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("84.0000"),
        )

        response = self.search(
            page="1",
            page_size="1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 1)

        self.assertEqual(
            response.data["results"][0]["name"],
            "Nearby Verified Hotel",
        )

        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

        # Existing search metadata must remain available.
        self.assertEqual(response.data["radius_km"], 10.0)
        self.assertEqual(response.data["sort_order"], "asc")
        self.assertEqual(
            response.data["search_location"]["latitude"],
            28.2096,
        )

        # Only the current page's hotel appears as a map marker.
        self.assertEqual(len(response.data["map_markers"]), 1)

    def test_nearby_search_preserves_descending_order_with_pagination(self):
        self.create_hotel(
            name="Farther Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("83.9900"),
        )

        self.create_hotel(
            name="Farthest Hotel",
            latitude=Decimal("28.2096"),
            longitude=Decimal("84.0000"),
        )

        response = self.search(
            sort_order="desc",
            page="1",
            page_size="1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sort_order"], "desc")

        self.assertEqual(
            response.data["results"][0]["name"],
            "Farthest Hotel",
        )

        self.assertIsNotNone(response.data["next"])

    def test_pagination_enforces_maximum_page_size(self):
        # Create 50 additional hotels.
        for number in range(50):
            self.create_hotel(
                name=f"Pagination Hotel {number:02d}",
            )

        response = self.destination_search(
            city="Pokhara",
            page_size="100",
        )

        self.assertEqual(response.status_code, 200)

        # 50 is the configured maximum page size.
        self.assertEqual(len(response.data["results"]), 50)

        # There are 51 hotels in total.
        self.assertEqual(response.data["count"], 51)

        # One hotel remains on the next page.
        self.assertIsNotNone(response.data["next"])


class MapBoundsHotelAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/hotels/map/"

        self.organisation = Organisation.objects.create(
            name="Map Bounds Test Organisation",
            status=Organisation.Status.ACTIVE,
        )

        self.map_hotel = self.create_hotel(
            name="Map Bounds Verified Hotel",
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
        city="Pokhara",
        area="Lakeside",
        star_rating=3,
        hotel_type="hotel",
    ):
        return Hotel.objects.create(
            organisation=organisation or self.organisation,
            name=name,
            country="Nepal",
            province="Gandaki",
            city=city,
            area=area,
            address=f"Test address, {city}",
            contact_phone="+9779800000000",
            latitude=latitude,
            longitude=longitude,
            is_verified=is_verified,
            status=status,
            is_deleted=is_deleted,
            star_rating=star_rating,
            hotel_type=hotel_type,
        )

    def search(self, **params):
        default_params = {
            "north": "28.30",
            "south": "28.10",
            "east": "84.10",
            "west": "83.80",
        }
        default_params.update(params)

        return self.client.get(self.url, default_params)

    # Basic map search

    def test_returns_hotel_inside_map_bounds(self):
        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        self.assertEqual(
            response.data["results"][0]["name"],
            "Map Bounds Verified Hotel",
        )

        self.assertEqual(len(response.data["map_markers"]), 1)

        self.assertEqual(
            response.data["map_markers"][0]["id"],
            self.map_hotel.id,
        )

    def test_excludes_hotel_outside_map_bounds(self):
        self.create_hotel(
            name="Outside Map Hotel",
            latitude=Decimal("28.5000"),
            longitude=Decimal("83.9856"),
        )

        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn("Outside Map Hotel", hotel_names)

    def test_excludes_hotel_without_coordinates(self):
        self.create_hotel(
            name="Hotel Without Coordinates",
        )

        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn(
            "Hotel Without Coordinates",
            hotel_names,
        )

    # Public visibility

    def test_excludes_unverified_hotels(self):
        self.create_hotel(
            name="Unverified Map Hotel",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
            is_verified=False,
        )

        response = self.search()

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn("Unverified Map Hotel", hotel_names)

    def test_excludes_hotel_with_inactive_organisation(self):
        inactive_organisation = Organisation.objects.create(
            name="Inactive Map Organisation",
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

    def test_excludes_deleted_hotels(self):
        self.create_hotel(
            name="Deleted Map Hotel",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
            is_deleted=True,
        )

        response = self.search()

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertNotIn("Deleted Map Hotel", hotel_names)

    # Optional filters

    def test_filters_by_city(self):
        self.create_hotel(
            name="Kathmandu Map Hotel",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
            city="Kathmandu",
            area="Thamel",
        )

        response = self.search(city="Pokhara")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filters_by_area(self):
        self.create_hotel(
            name="Different Area Hotel",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
            area="Sarangkot",
        )

        response = self.search(area="Lakeside")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_filters_by_minimum_star_rating(self):
        self.create_hotel(
            name="Four Star Map Hotel",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
            star_rating=4,
        )

        response = self.search(min_star_rating="4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["name"],
            "Four Star Map Hotel",
        )

    def test_rejects_invalid_hotel_type(self):
        response = self.search(hotel_type="palace")

        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_star_rating(self):
        response = self.search(min_star_rating="6")

        self.assertEqual(response.status_code, 400)

    # Map metadata and pagination

    def test_response_includes_map_bounds(self):
        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["map_bounds"],
            {
                "north": 28.30,
                "south": 28.10,
                "east": 84.10,
                "west": 83.80,
            },
        )

    def test_map_search_paginates_results(self):
        self.create_hotel(
            name="Second Map Hotel",
            latitude=Decimal("28.2200"),
            longitude=Decimal("83.9900"),
        )

        response = self.search(
            page="1",
            page_size="1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)

        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

        self.assertEqual(len(response.data["map_markers"]), 1)

    # Boundary validation
    def test_map_search_enforces_maximum_page_size(self):
        for number in range(50):
            self.create_hotel(
                name=f"Map Pagination Hotel {number:02d}",
                latitude=Decimal("28.2200"),
                longitude=Decimal("83.9900"),
            )

        response = self.search(page_size="100")

        self.assertEqual(response.status_code, 200)

        # 50 additional hotels + the original hotel
        self.assertEqual(response.data["count"], 51)

        # Configured maximum page size is 50
        self.assertEqual(len(response.data["results"]), 50)
        self.assertEqual(len(response.data["map_markers"]), 50)

        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
    def test_missing_boundary_returns_400(self):
        response = self.client.get(
            self.url,
            {
                "north": "28.30",
                "south": "28.10",
                "east": "84.10",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_boundary_text_returns_400(self):
        response = self.search(north="invalid")

        self.assertEqual(response.status_code, 400)

    def test_north_must_be_greater_than_south(self):
        response = self.search(
            north="20",
            south="30",
        )

        self.assertEqual(response.status_code, 400)

    def test_latitude_outside_valid_range_returns_400(self):
        response = self.search(north="95")

        self.assertEqual(response.status_code, 400)

    def test_longitude_outside_valid_range_returns_400(self):
        response = self.search(east="190")

        self.assertEqual(response.status_code, 400)

    def test_equal_longitude_boundaries_return_400(self):
        response = self.search(
            east="84",
            west="84",
        )

        self.assertEqual(response.status_code, 400)

    # International date-line handling

    def test_search_supports_international_date_line_crossing(self):
        self.create_hotel(
            name="Eastern Date Line Hotel",
            latitude=Decimal("0.0000"),
            longitude=Decimal("179.0000"),
        )

        self.create_hotel(
            name="Western Date Line Hotel",
            latitude=Decimal("0.0000"),
            longitude=Decimal("-179.0000"),
        )

        self.create_hotel(
            name="Outside Date Line Hotel",
            latitude=Decimal("0.0000"),
            longitude=Decimal("0.0000"),
        )

        response = self.search(
            north="20",
            south="-20",
            east="-170",
            west="170",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        hotel_names = [
            hotel["name"]
            for hotel in response.data["results"]
        ]

        self.assertIn("Eastern Date Line Hotel", hotel_names)
        self.assertIn("Western Date Line Hotel", hotel_names)
        self.assertNotIn("Outside Date Line Hotel", hotel_names)

    def test_map_search_filters_by_facility(self):
        hotel = self.create_hotel(
            name="Hotel With WiFi",
            latitude=Decimal("28.2100"),
            longitude=Decimal("83.9856"),
        )

        wifi = Facility.objects.create(
            name="Map Test WiFi",
            category=Facility.Category.GENERAL,
        )

        HotelFacility.objects.create(
            hotel=hotel,
            facility=wifi,
        )

        response = self.search(facility="WiFi")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            hotel.id,
        )