
from rest_framework import generics
from django.db.models import Prefetch

from .models import Hotel, RoomType
from .serializers import (
    HotelListSerializer,
    HotelDetailSerializer,
)
from .models import Hotel, RoomType, Membership
from .permissions import IsActiveOrganisationMember

# ==========================================================
# PUBLIC HOTEL LIST
# GET /api/hotels/
# ==========================================================

class PublicHotelListView(generics.ListAPIView):

    serializer_class = HotelListSerializer

    def get_queryset(self):
        return Hotel.objects.filter(
            status=Hotel.Status.ACTIVE,
            is_verified=True,
            organisation__status="active",
        ).select_related(
            "organisation"
        ).order_by(
            "name"
        )


# ==========================================================
# PUBLIC HOTEL DETAIL
# GET /api/hotels/<id>/
# ==========================================================

class PublicHotelDetailView(generics.RetrieveAPIView):

    serializer_class = HotelDetailSerializer

    def get_queryset(self):
        return Hotel.objects.filter(
            status=Hotel.Status.ACTIVE,
            is_verified=True,
            organisation__status="active",
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
        ).select_related(
            "organisation"
        ).order_by(
            "name"
        )