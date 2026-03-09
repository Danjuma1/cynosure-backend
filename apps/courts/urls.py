"""
URL patterns for courts endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CourtViewSet,
    DivisionViewSet,
    CourtroomViewSet,
    PanelViewSet,
    CourtRuleViewSet,
)

router = DefaultRouter()
router.register('', CourtViewSet, basename='court')
router.register('divisions', DivisionViewSet, basename='division')
router.register('courtrooms', CourtroomViewSet, basename='courtroom')
router.register('panels', PanelViewSet, basename='panel')
router.register('rules', CourtRuleViewSet, basename='court-rule')

urlpatterns = [
    path('', include(router.urls)),
]
