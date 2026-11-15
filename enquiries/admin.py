
from django.contrib import admin
from .models import TravellerRequirement, HotelMatch, HotelCall


@admin.register(TravellerRequirement)
class TravellerRequirementAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "city",
        "check_in_date",
        "check_out_date",
        "adults",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "country",
        "city",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "city",
        "original_request",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
@admin.register(HotelCall)
class HotelCallAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "hotel_match",
        "attempt_number",
        "status",
        "mode",
        "started_at",
        "completed_at",
        "created_at",
    )

    list_filter = (
        "status",
        "mode",
        "created_at",
    )

    search_fields = (
        "hotel_match__hotel__name",
        "hotel_match__requirement__city",
        "failure_reason",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)