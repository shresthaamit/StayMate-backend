from django.urls import path

from .views import (
    PublicHotelListView,
    PublicHotelDetailView,
    OrganisationHotelListView
)

urlpatterns = [
    path("", PublicHotelListView.as_view(), name="public-hotel-list"),
    path("<int:pk>/", PublicHotelDetailView.as_view(), name="public-hotel-detail"),
    path(
    "management/hotels/",
    OrganisationHotelListView.as_view(),
    name="organisation-hotel-list",
),
]