from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BriefRequestViewSet, BriefEngagementViewSet, BriefReviewViewSet

router = DefaultRouter()
router.register(r'requests', BriefRequestViewSet, basename='brief-request')
router.register(r'engagements', BriefEngagementViewSet, basename='brief-engagement')
router.register(r'reviews', BriefReviewViewSet, basename='brief-review')

urlpatterns = [
    path('', include(router.urls)),
]
