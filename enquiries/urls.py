
from django.urls import path

from .views import (
    TravellerRequirementListCreateView,
    TravellerRequirementDetailView,  HotelMatchGenerateView,HotelCallListCreateView,HotelCallDetailView, HotelCallSimulateView, TravellerResultsView,TravellerHotelCompareView
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
path(
    "matches/<int:match_id>/calls/",
    HotelCallListCreateView.as_view(),
    name="hotel-call-list-create",
),

path(
    "calls/<int:pk>/",
    HotelCallDetailView.as_view(),
    name="hotel-call-detail",
),
path(
    "calls/<int:pk>/simulate/",
    HotelCallSimulateView.as_view(),
    name="hotel-call-simulate",
),
path(
    "<int:requirement_id>/results/",
    TravellerResultsView.as_view(),
    name="requirement-results",
),

path(
    "<int:requirement_id>/compare/",
    TravellerHotelCompareView.as_view(),
    name="requirement-compare",
),

]
