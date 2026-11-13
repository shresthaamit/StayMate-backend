
from django.contrib import admin
from .models import TravellerRequirement


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
