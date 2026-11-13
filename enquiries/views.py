
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

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
