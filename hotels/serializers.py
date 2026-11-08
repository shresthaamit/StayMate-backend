
from rest_framework import serializers

from .models import (
    Hotel,
    Facility,
    HotelFacility,
    HotelContact,
    RoomType,
    RoomAvailability,
    HotelImage, Organisation,Membership
)


# ==========================================================
# FACILITY SERIALIZER
# ==========================================================

class FacilitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "category",
            "description",
        ]


# ==========================================================
# HOTEL FACILITY SERIALIZER
# ==========================================================

class HotelFacilitySerializer(serializers.ModelSerializer):

    facility = FacilitySerializer(read_only=True)

    class Meta:
        model = HotelFacility
        fields = [
            "id",
            "facility",
        ]


# ==========================================================
# HOTEL CONTACT SERIALIZER
# ==========================================================

class HotelContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = HotelContact
        fields = [
            "id",
            "name",
            "role",
            "phone_number",
            "email",
            "preferred_language",
            "is_primary",
        ]


# ==========================================================
# ROOM AVAILABILITY SERIALIZER
# ==========================================================

class RoomAvailabilitySerializer(serializers.ModelSerializer):

    class Meta:
        model = RoomAvailability
        fields = [
            "id",
            "date",
            "available_rooms",
            "price_per_night",
            "is_available",
            "updated_at",
        ]


# ==========================================================
# ROOM TYPE SERIALIZER
# ==========================================================

class RoomTypeSerializer(serializers.ModelSerializer):

    facilities = FacilitySerializer(many=True, read_only=True)

    availability_records = RoomAvailabilitySerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = RoomType
        fields = [
            "id",
            "name",
            "description",
            "max_occupancy",
            "adult_capacity",
            "child_capacity",
            "total_rooms",
            "bed_type",
            "number_of_beds",
            "base_price_per_night",
            "min_price_per_night",
            "max_price_per_night",
            "currency",
            "breakfast_included",
            "included_services",
            "facilities",
            "availability_records",
            "is_active",
        ]


# ==========================================================
# HOTEL IMAGE SERIALIZER
# ==========================================================

class HotelImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = HotelImage
        fields = [
            "id",
            "image",
            "image_type",
            "caption",
            "is_primary",
            "uploaded_at",
        ]


# ==========================================================
# HOTEL LIST SERIALIZER
# Used when displaying multiple hotels
# ==========================================================

class HotelListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Hotel
        fields = [
            "id",
            "name",
            "description",
            "hotel_type",
            "star_rating",
            "country",
            "province",
            "city",
            "area",
            "address",
            "latitude",
            "longitude",
            "contact_phone",
            "contact_email",
            "preferred_language",
            "check_in_time",
            "check_out_time",
            "is_verified",
        ]


# ==========================================================
# HOTEL DETAIL SERIALIZER
# Returns complete hotel information
# ==========================================================

class HotelDetailSerializer(serializers.ModelSerializer):

    organisation_name = serializers.CharField(
        source="organisation.name",
        read_only=True
    )

    hotel_facilities = HotelFacilitySerializer(
        many=True,
        read_only=True
    )

    contacts = HotelContactSerializer(
        many=True,
        read_only=True
    )

    room_types = RoomTypeSerializer(
        many=True,
        read_only=True
    )

    images = HotelImageSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Hotel
        fields = [
            "id",
            "organisation_name",
            "name",
            "description",
            "hotel_type",
            "star_rating",
            "website",
            "country",
            "province",
            "city",
            "area",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "nearby_landmarks",
            "contact_phone",
            "alternative_phone",
            "contact_email",
            "preferred_language",
            "preferred_contact_time",
            "check_in_time",
            "check_out_time",
            "cancellation_policy",
            "refund_policy",
            "child_policy",
            "extra_bed_policy",
            "pet_policy",
            "smoking_policy",
            "payment_methods",
            "tax_information",
            "deposit_policy",
            "status",
            "is_verified",
            "verified_at",
            "hotel_facilities",
            "contacts",
            "room_types",
            "images",
            "created_at",
            "updated_at",
        ]

class HotelCreateSerializer(serializers.ModelSerializer):

    organisation_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Hotel
        fields = [
            "id",
            "organisation_id",
            "name",
            "description",
            "hotel_type",
            "star_rating",
            "website",
            "country",
            "province",
            "city",
            "area",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "nearby_landmarks",
            "contact_phone",
            "alternative_phone",
            "contact_email",
            "preferred_language",
            "preferred_contact_time",
            "check_in_time",
            "check_out_time",
            "cancellation_policy",
            "refund_policy",
            "child_policy",
            "extra_bed_policy",
            "pet_policy",
            "smoking_policy",
            "payment_methods",
            "tax_information",
            "deposit_policy",
        ]
        read_only_fields = ["id"]

    def validate_organisation_id(self, value):

        request = self.context["request"]

        membership = Membership.objects.filter(
            user=request.user,
            organisation_id=value,
            is_active=True,
            organisation__status="active",
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).select_related("organisation").first()

        if not membership:
            raise serializers.ValidationError(
                "You do not have permission to register a hotel under this organisation."
            )

        return membership.organisation

    def create(self, validated_data):

        organisation = validated_data.pop("organisation_id")

        return Hotel.objects.create(
            organisation=organisation,
            **validated_data
        )

class HotelUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Hotel
        fields = [
            "id",
            "name",
            "description",
            "hotel_type",
            "star_rating",
            "website",
            "country",
            "province",
            "city",
            "area",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "nearby_landmarks",
            "contact_phone",
            "alternative_phone",
            "contact_email",
            "preferred_language",
            "preferred_contact_time",
            "check_in_time",
            "check_out_time",
            "cancellation_policy",
            "refund_policy",
            "child_policy",
            "extra_bed_policy",
            "pet_policy",
            "smoking_policy",
            "payment_methods",
            "tax_information",
            "deposit_policy",
        ]

        read_only_fields = ["id"]

    def to_internal_value(self, data):

        protected_fields = {
            "organisation",
            "organisation_id",
            "is_verified",
            "verified_at",
            "status",
        }

        submitted_fields = protected_fields.intersection(data.keys())

        if submitted_fields:
            raise serializers.ValidationError({
                field: "This field cannot be updated here."
                for field in submitted_fields
            })

        return super().to_internal_value(data)
