"""URL patterns for core endpoints."""
from django.urls import path
from .views import health_check, detailed_health_check, SystemInfoView

urlpatterns = [
    path('', health_check, name='health-check'),
    path('detailed/', detailed_health_check, name='health-check-detailed'),
    path('info/', SystemInfoView.as_view(), name='system-info'),
]
