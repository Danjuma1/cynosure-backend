"""URL patterns for admin panel endpoints."""
from django.urls import path
from .views import (
    DashboardView, AnalyticsView, ScraperControlView,
    UserManagementView, AuditLogView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='admin-dashboard'),
    path('analytics/', AnalyticsView.as_view(), name='admin-analytics'),
    path('scrapers/', ScraperControlView.as_view(), name='admin-scrapers'),
    path('users/', UserManagementView.as_view(), name='admin-users'),
    path('audit-logs/', AuditLogView.as_view(), name='admin-audit-logs'),
]
