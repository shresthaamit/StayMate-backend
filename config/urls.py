from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import EmailLoginView


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/accounts/', include('accounts.urls')),

    path(
        'api/accounts/login/',
        EmailLoginView.as_view(),
        name='token_obtain_pair'
    ),

    path(
        'api/accounts/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),
    path('api/hotels/', include('hotels.urls')),
    path("api/enquiries/", include("enquiries.urls")),
]
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )