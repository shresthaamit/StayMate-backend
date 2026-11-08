from django.urls import path

from .views import (
    PublicHotelListView,PublicHotelDetailView,OrganisationHotelListView,OrganisationHotelDetailView,HotelCreateView,HotelUpdateView
)

urlpatterns = [
    path("", PublicHotelListView.as_view(), name="public-hotel-list"),
    path("<int:pk>/", PublicHotelDetailView.as_view(), name="public-hotel-detail"),
    path(
    "management/hotels/", OrganisationHotelListView.as_view(),name="organisation-hotel-list"),
    path(
    "management/hotels/<int:pk>/",
    OrganisationHotelDetailView.as_view(),
    name="organisation-hotel-detail",
),
path(
    "management/hotels/create/",
    HotelCreateView.as_view(),
    name="organisation-hotel-create",
),
path(
    "management/hotels/<int:pk>/update/",
    HotelUpdateView.as_view(),
    name="organisation-hotel-update",
),
]