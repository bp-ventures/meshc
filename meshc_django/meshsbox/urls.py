"""URL configuration for meshc app."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.deposit, name='index'),  # Root redirects to deposit
    path('deposit/', views.deposit, name='deposit'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('link/', views.link, name='link'),
    path('api/link-token/', views.api_link_token, name='api_link_token'),
    path('api/withdraw-token/', views.api_withdraw_token, name='api_withdraw_token'),
    path('api/deposit-token/', views.api_deposit_token, name='api_deposit_token'),
    path('api/save-token/', views.api_save_token, name='api_save_token'),
    path('api/get-tokens/', views.api_get_tokens, name='api_get_tokens'),
    path('api/webhook/', views.api_webhook, name='api_webhook'),
]
