"""
URL patterns for cases endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CaseViewSet, CaseHearingViewSet, CaseNoteViewSet

router = DefaultRouter()
router.register('', CaseViewSet, basename='case')
router.register('hearings', CaseHearingViewSet, basename='case-hearing')
router.register('notes', CaseNoteViewSet, basename='case-note')

urlpatterns = [
    path('', include(router.urls)),
]
