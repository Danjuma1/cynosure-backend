from django.urls import path
from .views import PendingPolicyView, AcceptPolicyView

urlpatterns = [
    path('pending/', PendingPolicyView.as_view(), name='policy-pending'),
    path('accept/', AcceptPolicyView.as_view(), name='policy-accept'),
]
