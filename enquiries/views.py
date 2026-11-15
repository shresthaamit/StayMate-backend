
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .serializers import HotelMatchSerializer,TravellerRequirementSerializer, HotelCallSerializer
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
