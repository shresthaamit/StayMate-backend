
from django.urls import path

from .views import (
    TravellerRequirementListCreateView,
    TravellerRequirementDetailView,
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
]
