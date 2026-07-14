from django.urls import path
from .views import EngagementMessageListCreateView

urlpatterns = [
    path('', EngagementMessageListCreateView.as_view(), name='engagement-messages'),
]
