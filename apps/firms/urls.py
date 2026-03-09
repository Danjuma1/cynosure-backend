"""URL patterns for firms endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .models import LawFirmViewSet, FirmMembershipViewSet

router = DefaultRouter()
router.register('', LawFirmViewSet, basename='law-firm')
router.register('memberships', FirmMembershipViewSet, basename='firm-membership')

urlpatterns = [path('', include(router.urls))]
