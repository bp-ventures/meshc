"""URL configuration for meshc_django project."""
from django.urls import path, include

urlpatterns = [
    path('meshc/', include('meshsbox.urls')),
]
