"""
URL patterns for cause lists endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CauseListViewSet,
    CauseListEntryViewSet,
    CauseListSubscriptionViewSet,
)

router = DefaultRouter()
router.register('', CauseListViewSet, basename='cause-list')
router.register('entries', CauseListEntryViewSet, basename='cause-list-entry')
router.register('subscriptions', CauseListSubscriptionViewSet, basename='cause-list-subscription')

urlpatterns = [
    path('', include(router.urls)),
]
