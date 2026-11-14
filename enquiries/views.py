
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .serializers import HotelMatchSerializer
from .services import generate_hotel_matches
from .models import TravellerRequirement
from .serializers import TravellerRequirementSerializer


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
