
from rest_framework import generics
from django.db.models import Prefetch
from django.utils import timezone
from .models import Hotel, RoomType
from .serializers import (
    HotelListSerializer,
    HotelDetailSerializer,HotelCreateSerializer,HotelUpdateSerializer,
)
from .models import Hotel, RoomType, Membership
from .permissions import IsActiveOrganisationMember,IsOrganisationOwnerOrAdmin

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
            is_deleted=False,
        ).select_related(
            "organisation"
        ).order_by(
            "name"
        )

class PublicHotelDetailView(generics.RetrieveAPIView):

    serializer_class = HotelDetailSerializer

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