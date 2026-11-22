from django.urls import path

from .views import (
    PublicHotelListView,PublicHotelDetailView,OrganisationHotelListView,
    OrganisationHotelDetailView,HotelCreateView,HotelUpdateView,HotelDeleteView,NearbyHotelListView,
    DestinationHotelListView,MapBoundsHotelListView
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
path(
    "management/hotels/<int:pk>/delete/",
    HotelDeleteView.as_view(),
    name="organisation-hotel-delete",
),
path(
    "nearby/",
    NearbyHotelListView.as_view(),
    name="nearby-hotels",
),
path(
    "search/",
    DestinationHotelListView.as_view(),
    name="destination-hotel-search"
),
path(
    "map/",
    MapBoundsHotelListView.as_view(),
    name="map-hotel-search"
),
]