from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from .serializers import HotelMatchSerializer,TravellerRequirementSerializer, HotelCallSerializer,TravellerResultSerializer
from .services import generate_hotel_matches,run_simulated_hotel_call
from .models import TravellerRequirement, HotelCall, HotelMatch



class TravellerRequirementListCreateView(generics.ListCreateAPIView):
    serializer_class = TravellerRequirementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TravellerRequirement.objects.filter(
            user=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TravellerRequirementDetailView(generics.RetrieveAPIView):
    serializer_class = TravellerRequirementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TravellerRequirement.objects.filter(
            user=self.request.user
        )

class HotelMatchGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        requirement = get_object_or_404(
            TravellerRequirement,
            pk=pk,
            user=request.user
        )

        matches = generate_hotel_matches(requirement)

        serializer = HotelMatchSerializer(
            matches,
            many=True
        )

        return Response(
            {
                "requirement_id": requirement.id,
                "total_matches": len(matches),
                "matches": serializer.data,
            },
            status=status.HTTP_200_OK
        )
class HotelCallListCreateView(generics.ListCreateAPIView):
    serializer_class = HotelCallSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HotelCall.objects.filter(
            hotel_match__requirement__user=self.request.user
        ).select_related(
            "hotel_match",
            "hotel_match__hotel",
            "hotel_match__requirement",
        )

    def create(self, request, *args, **kwargs):
        match_id = self.kwargs["match_id"]

        with transaction.atomic():

            match = get_object_or_404(
                HotelMatch.objects.select_for_update(),
                pk=match_id,
                requirement__user=request.user,
            )

            if match.status in [
                HotelMatch.Status.RESPONDED,
                HotelMatch.Status.REJECTED,
            ]:
                raise ValidationError(
                    "Cannot create another call for this match."
                )

            active_call_exists = HotelCall.objects.filter(
                hotel_match=match,
                status__in=[
                    HotelCall.Status.QUEUED,
                    HotelCall.Status.IN_PROGRESS,
                ],
            ).exists()

            if active_call_exists:
                raise ValidationError(
                    "This hotel match already has an active call."
                )

            previous_attempts = HotelCall.objects.filter(
                hotel_match=match
            ).count()

            call = HotelCall.objects.create(
                hotel_match=match,
                attempt_number=previous_attempts + 1,
                mode=HotelCall.Mode.SIMULATED,
                status=HotelCall.Status.QUEUED,
            )

            match.status = HotelMatch.Status.CALL_PENDING
            match.save(update_fields=["status", "updated_at"])

        serializer = self.get_serializer(call)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


class HotelCallDetailView(generics.RetrieveAPIView):
    serializer_class = HotelCallSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HotelCall.objects.filter(
            hotel_match__requirement__user=self.request.user
        ).select_related(
            "hotel_match",
            "hotel_match__hotel",
            "hotel_match__requirement",
        )



class HotelCallSimulateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():

            call = get_object_or_404(
                HotelCall.objects.select_for_update(),
                pk=pk,
                hotel_match__requirement__user=request.user,
            )

            if call.status != HotelCall.Status.QUEUED:
                raise ValidationError(
                    "Only queued calls can be simulated."
                )

            call = run_simulated_hotel_call(call)

        serializer = HotelCallSerializer(call)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
    
class TravellerResultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, requirement_id):

        # Only allow the owner of the requirement to view results.
        requirement = get_object_or_404(
            TravellerRequirement,
            pk=requirement_id,
            user=request.user,
        )

        # Fetch matches and related data efficiently.
        matches = (
            HotelMatch.objects.filter(
                requirement=requirement
            )
            .select_related(
                "hotel",
                "matched_room_type",
                "requirement",
            )
            .prefetch_related(
                "hotel__hotel_facilities__facility",
                "matched_room_type__facilities",
                Prefetch(
                    "calls",
                    queryset=HotelCall.objects.order_by(
                        "-created_at",
                        "-id",
                    ),
                    to_attr="ordered_calls",
                ),
            )
            .order_by("-match_score", "created_at")
        )

        serializer = TravellerResultSerializer(
            matches,
            many=True,
        )

        results = list(serializer.data)

        # Read and validate price filters.
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")

        try:
            min_price = Decimal(min_price) if min_price is not None else None
            max_price = Decimal(max_price) if max_price is not None else None
        except InvalidOperation:
            raise ValidationError(
                {"price": "Price filters must be valid numbers."}
            )

        if (
            (min_price is not None and min_price < 0)
            or (max_price is not None and max_price < 0)
        ):
            raise ValidationError(
                {"price": "Price filters cannot be negative."}
            )

        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            raise ValidationError(
                {"price": "min_price cannot be greater than max_price."}
            )

        # Validate minimum star rating.
        min_star_rating = request.query_params.get("min_star_rating")

        if min_star_rating is not None:
            try:
                min_star_rating = int(min_star_rating)
            except ValueError:
                raise ValidationError(
                    {"min_star_rating": "Must be an integer from 1 to 5."}
                )

            if not 1 <= min_star_rating <= 5:
                raise ValidationError(
                    {"min_star_rating": "Must be between 1 and 5."}
                )

        # Validate boolean filters.
        def parse_boolean_filter(parameter_name):
            value = request.query_params.get(parameter_name)

            if value is None:
                return None

            value = value.lower()

            if value not in ["true", "false"]:
                raise ValidationError(
                    {
                        parameter_name:
                        "Use either true or false."
                    }
                )

            return value == "true"

        breakfast_filter = parse_boolean_filter("breakfast_included")
        airport_filter = parse_boolean_filter("airport_pickup")

        # Hotel type filter.
        hotel_type = request.query_params.get("hotel_type")

        # Apply filters.
        filtered_results = []

        for result in results:
            price = result["estimated_price_per_night"]

            if price is not None:
                price = Decimal(str(price))

            if min_price is not None:
                if price is None or price < min_price:
                    continue

            if max_price is not None:
                if price is None or price > max_price:
                    continue

            hotel = result["hotel"]
            room = result["matched_room_type"]
            latest_call = result["latest_call"]

            if min_star_rating is not None:
                star_rating = hotel["star_rating"]

                if star_rating is None or star_rating < min_star_rating:
                    continue

            if hotel_type is not None:
                if hotel["hotel_type"].lower() != hotel_type.lower():
                    continue

            if breakfast_filter is not None:
                breakfast = (
                    room.get("breakfast_included")
                    if room is not None
                    else None
                )

                if breakfast is not breakfast_filter:
                    continue

            if airport_filter is not None:
                response_data = (
                    latest_call.get("response_data") or {}
                    if latest_call
                    else {}
                )

                airport_pickup = response_data.get("airport_pickup")

                # Unknown values do not match either true or false.
                if airport_pickup is not airport_filter:
                    continue

            filtered_results.append(result)

        # Sorting.
        sort_by = request.query_params.get("sort_by")
        order = request.query_params.get("order")

        allowed_sort_fields = [
            "match_score",
            "price",
            "star_rating",
        ]

        if sort_by is not None and sort_by not in allowed_sort_fields:
            raise ValidationError(
                {
                    "sort_by":
                    "Choose match_score, price or star_rating."
                }
            )

        if order is not None and order not in ["asc", "desc"]:
            raise ValidationError(
                {"order": "Choose asc or desc."}
            )

        if order is not None and sort_by is None:
            raise ValidationError(
                {"order": "The order parameter requires sort_by."}
            )

        if sort_by is not None:
            if order is None:
                order = "asc" if sort_by == "price" else "desc"

            def get_sort_value(result):
                if sort_by == "match_score":
                    return result["match_score"]

                if sort_by == "price":
                    value = result["estimated_price_per_night"]
                    return Decimal(str(value)) if value is not None else None

                if sort_by == "star_rating":
                    return result["hotel"]["star_rating"]

            # Keep missing values at the end for both sort directions.
            available = [
                result for result in filtered_results
                if get_sort_value(result) is not None
            ]

            missing = [
                result for result in filtered_results
                if get_sort_value(result) is None
            ]

            available.sort(
                key=get_sort_value,
                reverse=(order == "desc"),
            )

            filtered_results = available + missing

        return Response(
            {
                "requirement_id": requirement.id,
                "destination": {
                    "country": requirement.country,
                    "province": requirement.province,
                    "city": requirement.city,
                    "area": requirement.area,
                },
                "check_in_date": requirement.check_in_date,
                "check_out_date": requirement.check_out_date,
                "guests": {
                    "adults": requirement.adults,
                    "children": requirement.children,
                    "rooms": requirement.rooms,
                },
                "total_matches": len(filtered_results),
                "results": filtered_results,
            },
            status=status.HTTP_200_OK,
        )

class TravellerHotelCompareView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, requirement_id):
        # Only the owner can compare hotels for this requirement.
        requirement = get_object_or_404(
            TravellerRequirement,
            pk=requirement_id,
            user=request.user,
        )

        # Read selected match IDs.
        raw_match_ids = request.query_params.get("match_ids")

        if not raw_match_ids:
            raise ValidationError({
                "match_ids": "Provide 2 to 4 match IDs, separated by commas."
            })

        try:
            match_ids = [
                int(value.strip())
                for value in raw_match_ids.split(",")
            ]
        except ValueError:
            raise ValidationError({
                "match_ids": "All match IDs must be valid integers."
            })

        # Validate selection count.
        if len(match_ids) < 2:
            raise ValidationError({
                "match_ids": "Select at least 2 hotels to compare."
            })

        if len(match_ids) > 4:
            raise ValidationError({
                "match_ids": "You can compare a maximum of 4 hotels."
            })

        # Reject duplicate IDs.
        if len(match_ids) != len(set(match_ids)):
            raise ValidationError({
                "match_ids": "Duplicate match IDs are not allowed."
            })

        # Fetch only matches belonging to this requirement.
        matches = (
            HotelMatch.objects.filter(
                requirement=requirement,
                id__in=match_ids,
            )
            .select_related(
                "hotel",
                "matched_room_type",
                "requirement",
            )
            .prefetch_related(
                "hotel__hotel_facilities__facility",
                "matched_room_type__facilities",
                Prefetch(
                    "calls",
                    queryset=HotelCall.objects.order_by(
                        "-created_at",
                        "-id",
                    ),
                    to_attr="ordered_calls",
                ),
            )
        )

        matches_by_id = {
            match.id: match
            for match in matches
        }

        # Every requested ID must belong to this requirement.
        if len(matches_by_id) != len(match_ids):
            raise ValidationError({
                "match_ids": (
                    "One or more selected matches do not exist "
                    "or do not belong to this requirement."
                )
            })

        # Preserve the order selected by the traveller.
        ordered_matches = [
            matches_by_id[match_id]
            for match_id in match_ids
        ]

        serializer = TravellerResultSerializer(
            ordered_matches,
            many=True,
        )

        return Response(
            {
                "requirement_id": requirement.id,
                "total_compared": len(ordered_matches),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
