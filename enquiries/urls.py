
from django.urls import path

from .views import (
    TravellerRequirementListCreateView,
    TravellerRequirementDetailView,  HotelMatchGenerateView,
)

urlpatterns = [
    path(
        "",
        TravellerRequirementListCreateView.as_view(),
        name="requirement-list-create"
    ),
    path(
        "<int:pk>/",
        TravellerRequirementDetailView.as_view(),
        name="requirement-detail"
    ),
    path(
    "<int:pk>/matches/",
    HotelMatchGenerateView.as_view(),
    name="requirement-matches"
),
]
