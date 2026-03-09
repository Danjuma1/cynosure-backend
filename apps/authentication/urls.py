"""
URL patterns for authentication endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SignupView,
    LoginView,
    LogoutView,
    CustomTokenRefreshView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    PasswordResetConfirmView,
    ChangePasswordView,
    ProfileView,
    EmailVerificationView,
    ResendVerificationView,
    UserFollowingViewSet,
    UserActivityView,
    DeviceTokenViewSet,
)

router = DefaultRouter()
router.register('followings', UserFollowingViewSet, basename='following')
router.register('device-tokens', DeviceTokenViewSet, basename='device-token')

urlpatterns = [
    # Authentication
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    
    # Password management
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Email verification
    path('verify-email/', EmailVerificationView.as_view(), name='verify-email'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    
    # Activity
    path('activity/', UserActivityView.as_view(), name='user-activity'),
    
    # Router URLs
    path('', include(router.urls)),
]
