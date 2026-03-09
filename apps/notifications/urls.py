"""
URL patterns for notifications endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    NotificationPreferenceViewSet,
    WebPushSubscriptionViewSet,
)

router = DefaultRouter()
router.register('', NotificationViewSet, basename='notification')
router.register('webpush', WebPushSubscriptionViewSet, basename='webpush')

urlpatterns = [
    path('preferences/', NotificationPreferenceViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
    }), name='notification-preferences'),
    path('', include(router.urls)),
]
