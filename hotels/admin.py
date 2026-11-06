
from django.contrib import admin
from .models import (
    Organisation,
    Membership,
    Hotel,
    Facility,
    HotelFacility,
    HotelContact,
    RoomType,
    RoomAvailability,
    HotelImage,
)


# ==========================================================
# ORGANISATION
# ==========================================================

class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ["user"]


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "business_email",
        "country",
        "status",
        "created_at",
    )
    list_filter = ("status", "country")
    search_fields = ("name", "legal_name", "business_email")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]


# ==========================================================
# MEMBERSHIP
# ==========================================================

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organisation",
        "role",
        "is_active",
        "joined_at",
    )
    list_filter = ("role", "is_active")
    search_fields = (
        "user__username",
        "user__email",
        "organisation__name",
    )
    autocomplete_fields = ["user", "organisation"]


# ==========================================================
# HOTEL
# ==========================================================

class HotelContactInline(admin.TabularInline):
    model = HotelContact
    extra = 0


class HotelFacilityInline(admin.TabularInline):
    model = HotelFacility
    extra = 0
    autocomplete_fields = ["facility"]


class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 0


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organisation",
        "hotel_type",
        "city",
        "country",
        "status",
        "is_verified",
    )
    list_filter = (
        "hotel_type",
        "status",
        "is_verified",
        "country",
    )
    search_fields = (
        "name",
        "city",
        "country",
        "contact_email",
    )
    autocomplete_fields = ["organisation"]
    inlines = [
        HotelContactInline,
        HotelFacilityInline,
        HotelImageInline,
    ]


# ==========================================================
# FACILITIES
# ==========================================================

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(HotelFacility)
class HotelFacilityAdmin(admin.ModelAdmin):
    list_display = ("hotel", "facility")
    search_fields = ("hotel__name", "facility__name")
    autocomplete_fields = ["hotel", "facility"]


# ==========================================================
# HOTEL CONTACTS
# ==========================================================

@admin.register(HotelContact)
class HotelContactAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "hotel",
        "role",
        "phone_number",
        "is_primary",
    )
    list_filter = ("role", "is_primary")
    search_fields = (
        "name",
        "hotel__name",
        "phone_number",
        "email",
    )
    autocomplete_fields = ["hotel"]


# ==========================================================
# ROOM TYPES
# ==========================================================

class RoomAvailabilityInline(admin.TabularInline):
    model = RoomAvailability
    extra = 0


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "hotel",
        "total_rooms",
        "base_price_per_night",
        "currency",
        "is_active",
    )
    list_filter = ("is_active", "bed_type", "currency")
    search_fields = ("name", "hotel__name")
    autocomplete_fields = ["hotel", "facilities"]
    inlines = [RoomAvailabilityInline]


# ==========================================================
# ROOM AVAILABILITY
# ==========================================================

@admin.register(RoomAvailability)
class RoomAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "room_type",
        "date",
        "available_rooms",
        "price_per_night",
        "is_available",
    )
    list_filter = ("date", "is_available")
    search_fields = ("room_type__name", "room_type__hotel__name")
    autocomplete_fields = ["room_type"]


# ==========================================================
# HOTEL IMAGES
# ==========================================================

@admin.register(HotelImage)
class HotelImageAdmin(admin.ModelAdmin):
    list_display = (
        "hotel",
        "image_type",
        "caption",
        "is_primary",
        "uploaded_at",
    )
    list_filter = ("image_type", "is_primary")
    search_fields = ("hotel__name", "caption")
    autocomplete_fields = ["hotel"]
