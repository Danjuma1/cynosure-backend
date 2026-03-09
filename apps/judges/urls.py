"""
URL patterns for judges endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    JudgeViewSet,
    JudgeAvailabilityViewSet,
    JudgeTransferViewSet,
    JudgeLeaveViewSet,
)

router = DefaultRouter()
router.register('', JudgeViewSet, basename='judge')
router.register('availability', JudgeAvailabilityViewSet, basename='judge-availability')
router.register('transfers', JudgeTransferViewSet, basename='judge-transfer')
router.register('leaves', JudgeLeaveViewSet, basename='judge-leave')

urlpatterns = [
    path('', include(router.urls)),
]
