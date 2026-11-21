from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import generics
from django.db.models import Prefetch
from django.utils import timezone
from .serializers import (
    HotelListSerializer,
    HotelDetailSerializer,HotelCreateSerializer,HotelUpdateSerializer,
)
from .models import Hotel, RoomType, Membership
from .permissions import IsActiveOrganisationMember,IsOrganisationOwnerOrAdmin
import math

from decimal import Decimal, InvalidOperation

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# ==========================================================
# PUBLIC HOTEL LIST
# GET /api/hotels/
# ==========================================================

class PublicHotelListView(generics.ListAPIView):

    serializer_class = HotelListSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        return Hotel.objects.filter(
            status=Hotel.Status.ACTIVE,
            is_verified=True,
            organisation__status="active",
            is_deleted=False,
        ).select_related(
            "organisation"
        ).order_by(
            "name"
        )

# ==========================================================
# NEARBY HOTELS
# GET /api/hotels/nearby/
# ==========================================================

class NearbyHotelListView(APIView):

    permission_classes = [AllowAny]

    EARTH_RADIUS_KM = 6371.0088
    DEFAULT_RADIUS_KM = Decimal("10")
    MAX_RADIUS_KM = Decimal("100")

    def get(self, request):

        # Validate latitude
        try:
            latitude = Decimal(request.query_params.get("latitude"))
        except (InvalidOperation, TypeError):
            return Response(
                {"error": "A valid latitude is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate longitude
        try:
            longitude = Decimal(request.query_params.get("longitude"))
        except (InvalidOperation, TypeError):
            return Response(
                {"error": "A valid longitude is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate coordinate ranges
        if not latitude.is_finite() or not -90 <= latitude <= 90:
            return Response(
                {"error": "Latitude must be between -90 and 90."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not longitude.is_finite() or not -180 <= longitude <= 180:
            return Response(
                {"error": "Longitude must be between -180 and 180."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate search radius
        try:
            radius_km = Decimal(
                request.query_params.get(
                    "radius_km",
                    str(self.DEFAULT_RADIUS_KM)
                )
            )
        except (InvalidOperation, TypeError):
            return Response(
                {"error": "A valid radius_km is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if (
            not radius_km.is_finite()
            or radius_km <= 0
            or radius_km > self.MAX_RADIUS_KM
        ):
            return Response(
                {"error": "Radius must be greater than 0 and at most 100 km."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_lat = float(latitude)
        user_lon = float(longitude)
        # Validate distance sorting order
        sort_order = request.query_params.get("sort_order", "asc").lower()

        if sort_order not in ["asc", "desc"]:
            return Response(
                {"error": "sort_order must be either 'asc' or 'desc'."},
                status=status.HTTP_400_BAD_REQUEST
            )
                # Retrieve only publicly visible hotels with coordinates
       
        hotels = Hotel.objects.filter(
            status=Hotel.Status.ACTIVE,
            is_verified=True,
            organisation__status="active",
            is_deleted=False,
        ).exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).select_related(
            "organisation"
        )

        # Optional city filter
        city = request.query_params.get("city")
        if city:
            hotels = hotels.filter(city__icontains=city.strip())

        # Optional area filter
        area = request.query_params.get("area")
        if area:
            hotels = hotels.filter(area__icontains=area.strip())

        # Optional minimum star rating
        min_star_rating = request.query_params.get("min_star_rating")
        if min_star_rating:
            try:
                min_star_rating = int(min_star_rating)
            except ValueError:
                return Response(
                    {"error": "min_star_rating must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not 1 <= min_star_rating <= 5:
                return Response(
                    {"error": "min_star_rating must be between 1 and 5."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            hotels = hotels.filter(star_rating__gte=min_star_rating)

        # Optional maximum star rating
        max_star_rating = request.query_params.get("max_star_rating")
        if max_star_rating:
            try:
                max_star_rating = int(max_star_rating)
            except ValueError:
                return Response(
                    {"error": "max_star_rating must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not 1 <= max_star_rating <= 5:
                return Response(
                    {"error": "max_star_rating must be between 1 and 5."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            hotels = hotels.filter(star_rating__lte=max_star_rating)

        # Minimum rating cannot exceed maximum rating
        if (
            min_star_rating
            and max_star_rating
            and min_star_rating > max_star_rating
        ):
            return Response(
                {"error": "Minimum star rating cannot exceed maximum rating."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Optional hotel type filter
        hotel_type = request.query_params.get("hotel_type")
        if hotel_type:
            valid_hotel_types = Hotel.HotelType.values

            if hotel_type not in valid_hotel_types:
                return Response(
                    {
                        "error": "Invalid hotel_type.",
                        "valid_choices": valid_hotel_types,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            hotels = hotels.filter(hotel_type=hotel_type)

        # Optional facility filter
        facility = request.query_params.get("facility")
        if facility:
            hotels = hotels.filter(
                hotel_facilities__facility__name__icontains=facility.strip()
            ).distinct()


        nearby_hotels = []

        # Calculate distance using the Haversine formula
        for hotel in hotels:

            hotel_lat = float(hotel.latitude)
            hotel_lon = float(hotel.longitude)

            lat1 = math.radians(user_lat)
            lon1 = math.radians(user_lon)
            lat2 = math.radians(hotel_lat)
            lon2 = math.radians(hotel_lon)

            delta_lat = lat2 - lat1
            delta_lon = lon2 - lon1

            a = (
                math.sin(delta_lat / 2) ** 2
                + math.cos(lat1)
                * math.cos(lat2)
                * math.sin(delta_lon / 2) ** 2
            )

            # Protect against floating-point rounding errors
            a = min(1.0, max(0.0, a))

            distance = (
                2
                * self.EARTH_RADIUS_KM
                * math.asin(math.sqrt(a))
            )

            if distance <= float(radius_km):
                nearby_hotels.append({
                    "hotel": hotel,
                    "distance_km": round(distance, 2),
                })

        # Nearest hotels first
                nearby_hotels.sort(
            key=lambda item: item["hotel"].name
        )

        nearby_hotels.sort(
            key=lambda item: item["distance_km"],
            reverse=(sort_order == "desc")
        )

        # Serialize hotel information and include distance
        results = []

        for item in nearby_hotels:
            hotel_data = HotelListSerializer(item["hotel"]).data
            hotel_data["distance_km"] = item["distance_km"]
            results.append(hotel_data)

        return Response({
        "count": len(results),
        "radius_km": float(radius_km),
        "sort_order": sort_order,
        "search_location": {
            "latitude": user_lat,
            "longitude": user_lon,
        },
        "results": results,
    })

class PublicHotelDetailView(generics.RetrieveAPIView):

    serializer_class = HotelDetailSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        return Hotel.objects.filter(
            status=Hotel.Status.ACTIVE,
            is_verified=True,
            organisation__status="active",
            is_deleted=False,
        ).select_related(
            "organisation"
        ).prefetch_related(
            "hotel_facilities__facility",
            "contacts",
            Prefetch(
                "room_types",
                queryset=RoomType.objects.filter(
                    is_active=True
                ).prefetch_related(
                    "facilities",
                    "availability_records",
                )
            ),
            "images",
        )

    
class OrganisationHotelListView(generics.ListAPIView):

    serializer_class = HotelListSerializer
    permission_classes = [IsActiveOrganisationMember]

    def get_queryset(self):
        active_organisations = Membership.objects.filter(
            user=self.request.user,
            is_active=True,
            organisation__status="active",
        ).values_list(
            "organisation_id",
            flat=True,
        )

        return Hotel.objects.filter(
            organisation_id__in=active_organisations,
            is_deleted=False,
        ).select_related(
            "organisation"
        ).order_by(
            "name"
        )
class OrganisationHotelDetailView(generics.RetrieveAPIView):
    serializer_class = HotelDetailSerializer
    permission_classes = [IsActiveOrganisationMember]

    def get_queryset(self):

        active_organisations = Membership.objects.filter(
            user=self.request.user,
            is_active=True,
            organisation__status="active",
        ).values_list(
            "organisation_id",
            flat=True,
        )

        return Hotel.objects.filter(
            organisation_id__in=active_organisations,
            is_deleted=False,
        ).select_related(
            "organisation"
        ).prefetch_related(
            "hotel_facilities__facility",
            "contacts",
            Prefetch(
                "room_types",
                queryset=RoomType.objects.filter(
                    is_active=True
                ).prefetch_related(
                    "facilities",
                    "availability_records",
                )
            ),
            "images",
        )

class HotelCreateView(generics.CreateAPIView):
    serializer_class = HotelCreateSerializer
    permission_classes = [IsOrganisationOwnerOrAdmin]



class HotelUpdateView(generics.UpdateAPIView):

    serializer_class = HotelUpdateSerializer
    permission_classes = [IsOrganisationOwnerOrAdmin]

    def get_queryset(self):
        active_organisations = Membership.objects.filter(
            user=self.request.user,
            is_active=True,
            organisation__status="active",
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).values_list(
            "organisation_id",
            flat=True,
        )

        return Hotel.objects.filter(
            organisation_id__in=active_organisations,
            is_deleted=False,
        )

# ==========================================================
# HOTEL SOFT DELETE
# DELETE /api/hotels/management/hotels/<id>/delete/
# ==========================================================

class HotelDeleteView(generics.DestroyAPIView):

    permission_classes = [IsOrganisationOwnerOrAdmin]

    def get_queryset(self):
        active_organisations = Membership.objects.filter(
            user=self.request.user,
            is_active=True,
            organisation__status="active",
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).values_list(
            "organisation_id",
            flat=True,
        )

        return Hotel.objects.filter(
            organisation_id__in=active_organisations,
            is_deleted=False,
        )

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()

        instance.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )


# ==========================================================
# DESTINATION-BASED HOTEL SEARCH
# GET /api/hotels/search/
# ==========================================================

class DestinationHotelListView(APIView):

    permission_classes = [AllowAny]

    def get(self, request):

        # Read destination parameters
        city = request.query_params.get("city", "").strip()
        area = request.query_params.get("area", "").strip()

        # At least one destination field is required
        if not city and not area:
            return Response(
                {
                    "error": "Please provide at least a city or area."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve publicly visible hotels
        hotels = Hotel.objects.filter(
            status=Hotel.Status.ACTIVE,
            is_verified=True,
            organisation__status="active",
            is_deleted=False,
        ).select_related(
            "organisation"
        )

        # Filter by city
        if city:
            hotels = hotels.filter(
                city__icontains=city
            )

        # Filter by area
        if area:
            hotels = hotels.filter(
                area__icontains=area
            )

        # Keep results in a predictable order
        hotels = hotels.order_by("name")

        # Serialize hotel information
        results = HotelListSerializer(
            hotels,
            many=True
        ).data

        return Response({
            "count": len(results),
            "search_destination": {
                "city": city or None,
                "area": area or None,
            },
            "results": results,
        })
