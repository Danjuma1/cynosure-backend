"""URL patterns for e-filing endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .models import FilingViewSet

router = DefaultRouter()
router.register('', FilingViewSet, basename='filing')

urlpatterns = [path('', include(router.urls))]
