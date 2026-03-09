"""URL patterns for search endpoints."""
from django.urls import path
from .views import GlobalSearchView, CaseSearchView, CauseListSearchView

urlpatterns = [
    path('', GlobalSearchView.as_view(), name='global-search'),
    path('cases/', CaseSearchView.as_view(), name='case-search'),
    path('cause-lists/', CauseListSearchView.as_view(), name='cause-list-search'),
]
