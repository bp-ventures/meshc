"""URL configuration for meshc_django project."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('meshc/', include('meshsbox.urls')),
]
