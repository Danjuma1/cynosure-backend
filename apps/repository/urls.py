"""URL patterns for repository endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .models import DocumentCategoryViewSet, LegalDocumentViewSet, DocumentBookmarkViewSet

router = DefaultRouter()
router.register('categories', DocumentCategoryViewSet, basename='document-category')
router.register('documents', LegalDocumentViewSet, basename='legal-document')
router.register('bookmarks', DocumentBookmarkViewSet, basename='document-bookmark')

urlpatterns = [path('', include(router.urls))]
