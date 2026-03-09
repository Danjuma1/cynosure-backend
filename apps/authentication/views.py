"""
Authentication views for Cynosure.
"""
from django.conf import settings
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.common.utils import generate_otp, send_notification_email
from apps.common.permissions import IsOwnerOrAdmin, IsSuperAdmin
from .models import User, UserFollowing, OTPCode, UserActivity, DeviceToken
from .serializers import (
    UserSignupSerializer,
    UserLoginSerializer,
    TokenResponseSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetOTPVerifySerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
    UserFollowingSerializer,
    FollowSerializer,
    UserActivitySerializer,
    DeviceTokenSerializer,
    EmailVerificationSerializer,
    UserListSerializer,
)


@extend_schema(tags=['Authentication'])
class SignupView(generics.CreateAPIView):
    """
    User registration endpoint.
    
    Creates a new user account and sends a verification email.
    """
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate verification OTP
        otp = generate_otp()
        OTPCode.objects.create(
            user=user,
            code=otp,
            purpose='email_verification',
            expires_at=timezone.now() + timezone.timedelta(
                minutes=settings.CYNOSURE_SETTINGS['OTP_EXPIRY_MINUTES']
            )
        )
        
        # Send verification email
        send_notification_email(
            to_email=user.email,
            subject='Verify your Cynosure account',
            template_name='email_verification',
            context={
                'user': user,
                'otp': otp,
                'expiry_minutes': settings.CYNOSURE_SETTINGS['OTP_EXPIRY_MINUTES'],
            }
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Account created successfully. Please verify your email.',
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserProfileSerializer(user).data,
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Authentication'])
class LoginView(APIView):
    """
    User login endpoint.
    
    Authenticates user and returns JWT tokens.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'auth'
    
    @extend_schema(
        request=UserLoginSerializer,
        responses={200: TokenResponseSerializer}
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Update last login info
        user.last_login = timezone.now()
        user.last_login_ip = self.get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])
        
        # Log activity
        UserActivity.objects.create(
            user=user,
            activity_type='login',
            ip_address=user.last_login_ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'data': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserProfileSerializer(user).data,
            }
        })
    
    def get_client_ip(self, request):
        """Get client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema(tags=['Authentication'])
class LogoutView(APIView):
    """
    User logout endpoint.
    
    Blacklists the refresh token.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='logout',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            
            return Response({
                'success': True,
                'message': 'Logged out successfully.'
            })
        except Exception:
            return Response({
                'success': True,
                'message': 'Logged out successfully.'
            })


@extend_schema(tags=['Authentication'])
class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh view."""
    pass


@extend_schema(tags=['Authentication'])
class PasswordResetRequestView(APIView):
    """
    Request password reset OTP.
    
    Sends an OTP to the user's email.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'auth'
    
    @extend_schema(request=PasswordResetRequestSerializer)
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email__iexact=email)
        
        # Invalidate previous OTPs
        OTPCode.objects.filter(
            user=user,
            purpose='password_reset',
            is_used=False
        ).update(is_used=True)
        
        # Generate new OTP
        otp = generate_otp()
        OTPCode.objects.create(
            user=user,
            code=otp,
            purpose='password_reset',
            expires_at=timezone.now() + timezone.timedelta(
                minutes=settings.CYNOSURE_SETTINGS['OTP_EXPIRY_MINUTES']
            )
        )
        
        # Send email
        send_notification_email(
            to_email=user.email,
            subject='Reset your Cynosure password',
            template_name='password_reset',
            context={
                'user': user,
                'otp': otp,
                'expiry_minutes': settings.CYNOSURE_SETTINGS['OTP_EXPIRY_MINUTES'],
            }
        )
        
        return Response({
            'success': True,
            'message': 'Password reset OTP has been sent to your email.'
        })


@extend_schema(tags=['Authentication'])
class PasswordResetVerifyView(APIView):
    """
    Verify password reset OTP.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'auth'
    
    @extend_schema(request=PasswordResetOTPVerifySerializer)
    def post(self, request):
        serializer = PasswordResetOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response({
            'success': True,
            'message': 'OTP verified successfully. You can now reset your password.'
        })


@extend_schema(tags=['Authentication'])
class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with new password.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'auth'
    
    @extend_schema(request=PasswordResetConfirmSerializer)
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Password reset successfully. You can now login with your new password.'
        })


@extend_schema(tags=['Authentication'])
class ChangePasswordView(APIView):
    """
    Change password for authenticated user.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(request=ChangePasswordSerializer)
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='password_change',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        return Response({
            'success': True,
            'message': 'Password changed successfully.'
        })


@extend_schema(tags=['Authentication'])
class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update user profile.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='profile_update',
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'updated_fields': list(request.data.keys())},
        )
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully.',
            'data': response.data,
        })


@extend_schema(tags=['Authentication'])
class EmailVerificationView(APIView):
    """
    Verify email with OTP.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(request=EmailVerificationSerializer)
    def post(self, request):
        serializer = EmailVerificationSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Email verified successfully.'
        })


@extend_schema(tags=['Authentication'])
class ResendVerificationView(APIView):
    """
    Resend email verification OTP.
    """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'auth'
    
    def post(self, request):
        user = request.user
        
        if user.is_verified:
            return Response({
                'success': False,
                'message': 'Email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Invalidate previous OTPs
        OTPCode.objects.filter(
            user=user,
            purpose='email_verification',
            is_used=False
        ).update(is_used=True)
        
        # Generate new OTP
        otp = generate_otp()
        OTPCode.objects.create(
            user=user,
            code=otp,
            purpose='email_verification',
            expires_at=timezone.now() + timezone.timedelta(
                minutes=settings.CYNOSURE_SETTINGS['OTP_EXPIRY_MINUTES']
            )
        )
        
        # Send email
        send_notification_email(
            to_email=user.email,
            subject='Verify your Cynosure account',
            template_name='email_verification',
            context={
                'user': user,
                'otp': otp,
                'expiry_minutes': settings.CYNOSURE_SETTINGS['OTP_EXPIRY_MINUTES'],
            }
        )
        
        return Response({
            'success': True,
            'message': 'Verification OTP has been sent to your email.'
        })


@extend_schema_view(
    list=extend_schema(tags=['Authentication']),
    create=extend_schema(tags=['Authentication']),
    destroy=extend_schema(tags=['Authentication']),
)
class UserFollowingViewSet(ModelViewSet):
    """
    Manage user followings (courts, judges, cases, categories).
    """
    serializer_class = UserFollowingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        queryset = UserFollowing.objects.filter(user=self.request.user)
        
        # Filter by type
        follow_type = self.request.query_params.get('type')
        if follow_type:
            queryset = queryset.filter(follow_type=follow_type)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def follow(self, request):
        """Follow a court, judge, case, or category."""
        serializer = FollowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        following, created = UserFollowing.objects.get_or_create(
            user=request.user,
            follow_type=serializer.validated_data['follow_type'],
            object_id=serializer.validated_data['object_id'],
            defaults={
                'notifications_enabled': serializer.validated_data.get('notifications_enabled', True)
            }
        )
        
        if not created:
            return Response({
                'success': False,
                'message': 'Already following this item.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='follow',
            details={
                'follow_type': following.follow_type,
                'object_id': str(following.object_id),
            }
        )
        
        return Response({
            'success': True,
            'message': 'Successfully followed.',
            'data': UserFollowingSerializer(following).data,
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def unfollow(self, request):
        """Unfollow a court, judge, case, or category."""
        serializer = FollowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        deleted, _ = UserFollowing.objects.filter(
            user=request.user,
            follow_type=serializer.validated_data['follow_type'],
            object_id=serializer.validated_data['object_id'],
        ).delete()
        
        if not deleted:
            return Response({
                'success': False,
                'message': 'Not following this item.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='unfollow',
            details={
                'follow_type': serializer.validated_data['follow_type'],
                'object_id': str(serializer.validated_data['object_id']),
            }
        )
        
        return Response({
            'success': True,
            'message': 'Successfully unfollowed.',
        })


@extend_schema(tags=['Authentication'])
class UserActivityView(generics.ListAPIView):
    """
    Get user activity logs.
    """
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserActivity.objects.filter(user=self.request.user)[:100]


@extend_schema_view(
    list=extend_schema(tags=['Authentication']),
    create=extend_schema(tags=['Authentication']),
    destroy=extend_schema(tags=['Authentication']),
)
class DeviceTokenViewSet(ModelViewSet):
    """
    Manage device tokens for push notifications.
    """
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save()
    
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])
