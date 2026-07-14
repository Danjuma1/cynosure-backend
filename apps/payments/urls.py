from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FeeConfigView, BankAccountViewSet, BanksListView,
    EscrowInitializeView, EscrowVerifyView, PaystackWebhookView,
)

router = DefaultRouter()
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-account')

urlpatterns = [
    path('fee-config/', FeeConfigView.as_view(), name='fee-config'),
    path('banks/', BanksListView.as_view(), name='banks-list'),
    path('escrow/<uuid:engagement_id>/initialize/', EscrowInitializeView.as_view(), name='escrow-initialize'),
    path('escrow/<uuid:engagement_id>/verify/', EscrowVerifyView.as_view(), name='escrow-verify'),
    path('webhooks/paystack/', PaystackWebhookView.as_view(), name='paystack-webhook'),
    path('', include(router.urls)),
]
