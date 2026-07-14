from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.payments.views import EngagementEscrowView
from .views import (
    BriefRequestViewSet, BriefEngagementViewSet, BriefReviewViewSet,
    ApplicationOfferListCreateView, AcceptOfferView, DeclineOfferView,
)

router = DefaultRouter()
router.register(r'requests', BriefRequestViewSet, basename='brief-request')
router.register(r'engagements', BriefEngagementViewSet, basename='brief-engagement')
router.register(r'reviews', BriefReviewViewSet, basename='brief-review')

urlpatterns = [
    path('engagements/<uuid:engagement_id>/messages/', include('apps.messaging.urls')),
    path('engagements/<uuid:engagement_id>/escrow/', EngagementEscrowView.as_view(), name='engagement-escrow'),
    path('applications/<uuid:application_id>/offers/', ApplicationOfferListCreateView.as_view(), name='application-offers'),
    path('applications/<uuid:application_id>/offers/<uuid:offer_id>/accept/', AcceptOfferView.as_view(), name='application-offer-accept'),
    path('applications/<uuid:application_id>/offers/<uuid:offer_id>/decline/', DeclineOfferView.as_view(), name='application-offer-decline'),
    path('', include(router.urls)),
]
