from django.urls import path

from .views import (
    PublicHotelListView,
    PublicHotelDetailView,
)

urlpatterns = [
    path("", PublicHotelListView.as_view(), name="public-hotel-list"),
    path("<int:pk>/", PublicHotelDetailView.as_view(), name="public-hotel-detail"),
]