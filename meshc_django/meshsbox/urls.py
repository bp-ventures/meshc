"""URL configuration for meshc app."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/link-token/', views.api_link_token, name='api_link_token'),
    path('api/save-token/', views.api_save_token, name='api_save_token'),
    path('api/webhook/', views.api_webhook, name='api_webhook'),
]
