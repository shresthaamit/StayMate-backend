
from rest_framework import serializers
from .models import TravellerRequirement


class TravellerRequirementSerializer(serializers.ModelSerializer):

    class Meta:
        model = TravellerRequirement
        fields = [
            "id",
            "user",
            "original_request",
            "country",
            "province",
            "city",
            "area",
            "check_in_date",
            "check_out_date",
            "adults",
            "children",
            "rooms",
            "min_budget_per_night",
            "max_budget_per_night",
            "currency",
            "preferred_hotel_types",
            "minimum_star_rating",
            "required_facilities",
            "special_requests",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "user",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        check_in = data.get(
            "check_in_date",
            getattr(self.instance, "check_in_date", None)
        )
        check_out = data.get(
            "check_out_date",
            getattr(self.instance, "check_out_date", None)
        )

        min_budget = data.get(
            "min_budget_per_night",
            getattr(self.instance, "min_budget_per_night", None)
        )
        max_budget = data.get(
            "max_budget_per_night",
            getattr(self.instance, "max_budget_per_night", None)
        )

        errors = {}

        if check_in and check_out and check_out <= check_in:
            errors["check_out_date"] = (
                "Check-out date must be after check-in date."
            )

        if (
            min_budget is not None
            and max_budget is not None
            and min_budget > max_budget
        ):
            errors["max_budget_per_night"] = (
                "Maximum budget must be greater than or equal to minimum budget."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return data
