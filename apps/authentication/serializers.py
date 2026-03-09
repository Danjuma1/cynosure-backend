"""
Serializers for authentication endpoints.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.utils import generate_otp
from .models import User, UserFollowing, OTPCode, UserActivity, DeviceToken


class UserSignupSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'phone_number',
            'user_type', 'bar_number', 'year_of_call',
        ]
        extra_kwargs = {
            'user_type': {'default': 'lawyer'},
        }
    
    def validate_email(self, value):
        """Validate email is unique."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_password(self, value):
        """Validate password strength."""
        validate_password(value)
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': "Passwords don't match."
            })
        return attrs
    
    def create(self, validated_data):
        """Create new user."""
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        password = attrs.get('password')
        
        # Check if user exists
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'email': 'No account found with this email.'
            })
        
        # Check if account is locked
        if user.is_locked():
            raise serializers.ValidationError({
                'email': 'Account is temporarily locked. Please try again later.'
            })
        
        # Check if account is active
        if not user.is_active:
            raise serializers.ValidationError({
                'email': 'This account has been deactivated.'
            })
        
        # Authenticate
        user = authenticate(email=email, password=password)
        if not user:
            # Increment failed attempts
            try:
                u = User.objects.get(email__iexact=email)
                u.increment_failed_attempts()
            except User.DoesNotExist:
                pass
            
            raise serializers.ValidationError({
                'password': 'Invalid password.'
            })
        
        # Reset failed attempts on successful login
        user.reset_failed_attempts()
        
        attrs['user'] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response."""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.SerializerMethodField()
    
    def get_user(self, obj):
        return UserProfileSerializer(obj['user']).data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'title', 'phone_number', 'user_type', 'profile_picture',
            'bar_number', 'year_of_call', 'specializations', 'bio',
            'is_verified', 'email_notifications', 'push_notifications',
            'sms_notifications', 'two_factor_enabled',
            'date_joined', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'email', 'user_type', 'is_verified',
            'date_joined', 'created_at', 'updated_at',
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'title', 'phone_number',
            'profile_picture', 'bar_number', 'year_of_call',
            'specializations', 'bio', 'email_notifications',
            'push_notifications', 'sms_notifications',
        ]


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Check if email exists."""
        if not User.objects.filter(email__iexact=value, is_active=True).exists():
            raise serializers.ValidationError("No active account found with this email.")
        return value.lower()


class PasswordResetOTPVerifySerializer(serializers.Serializer):
    """Serializer for verifying password reset OTP."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=10)
    
    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        otp = attrs.get('otp')
        
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': 'Invalid email.'})
        
        # Get latest valid OTP
        otp_obj = OTPCode.objects.filter(
            user=user,
            code=otp,
            purpose='password_reset',
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if not otp_obj:
            raise serializers.ValidationError({'otp': 'Invalid or expired OTP.'})
        
        if otp_obj.attempts >= 5:
            raise serializers.ValidationError({'otp': 'Too many attempts. Request a new OTP.'})
        
        otp_obj.attempts += 1
        otp_obj.save(update_fields=['attempts'])
        
        attrs['user'] = user
        attrs['otp_obj'] = otp_obj
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=10)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate_new_password(self, value):
        """Validate password strength."""
        validate_password(value)
        return value
    
    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        otp = attrs.get('otp')
        
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': "Passwords don't match."
            })
        
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': 'Invalid email.'})
        
        # Verify OTP
        otp_obj = OTPCode.objects.filter(
            user=user,
            code=otp,
            purpose='password_reset',
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if not otp_obj:
            raise serializers.ValidationError({'otp': 'Invalid or expired OTP.'})
        
        attrs['user'] = user
        attrs['otp_obj'] = otp_obj
        return attrs
    
    def save(self):
        """Reset password and mark OTP as used."""
        user = self.validated_data['user']
        otp_obj = self.validated_data['otp_obj']
        
        user.set_password(self.validated_data['new_password'])
        user.password_changed_at = timezone.now()
        user.save(update_fields=['password', 'password_changed_at'])
        
        otp_obj.mark_used()
        
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (authenticated user)."""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate_new_password(self, value):
        """Validate password strength."""
        validate_password(value)
        return value
    
    def validate_current_password(self, value):
        """Verify current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': "Passwords don't match."
            })
        
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': "New password must be different from current password."
            })
        
        return attrs
    
    def save(self):
        """Change password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.password_changed_at = timezone.now()
        user.save(update_fields=['password', 'password_changed_at'])
        return user


class UserFollowingSerializer(serializers.ModelSerializer):
    """Serializer for user following relationships."""
    
    class Meta:
        model = UserFollowing
        fields = [
            'id', 'follow_type', 'object_id',
            'notifications_enabled', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class FollowSerializer(serializers.Serializer):
    """Serializer for follow/unfollow actions."""
    follow_type = serializers.ChoiceField(choices=UserFollowing.FOLLOW_TYPE_CHOICES)
    object_id = serializers.UUIDField()
    notifications_enabled = serializers.BooleanField(default=True)


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activity logs."""
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'activity_type', 'details',
            'ip_address', 'created_at',
        ]
        read_only_fields = fields


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for device tokens."""
    
    class Meta:
        model = DeviceToken
        fields = ['id', 'token', 'platform', 'device_name', 'is_active']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """Create or update device token."""
        user = self.context['request'].user
        token, created = DeviceToken.objects.update_or_create(
            user=user,
            token=validated_data['token'],
            defaults={
                'platform': validated_data['platform'],
                'device_name': validated_data.get('device_name', ''),
                'is_active': True,
            }
        )
        return token


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""
    otp = serializers.CharField(max_length=10)
    
    def validate(self, attrs):
        user = self.context['request'].user
        otp = attrs.get('otp')
        
        otp_obj = OTPCode.objects.filter(
            user=user,
            code=otp,
            purpose='email_verification',
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if not otp_obj:
            raise serializers.ValidationError({'otp': 'Invalid or expired OTP.'})
        
        attrs['otp_obj'] = otp_obj
        return attrs
    
    def save(self):
        """Mark user as verified."""
        user = self.context['request'].user
        otp_obj = self.validated_data['otp_obj']
        
        user.is_verified = True
        user.verified_at = timezone.now()
        user.save(update_fields=['is_verified', 'verified_at'])
        
        otp_obj.mark_used()
        
        return user


class TwoFactorSetupSerializer(serializers.Serializer):
    """Serializer for setting up 2FA."""
    secret = serializers.CharField(read_only=True)
    qr_code_url = serializers.CharField(read_only=True)


class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer for verifying 2FA code."""
    code = serializers.CharField(max_length=6)


class UserListSerializer(serializers.ModelSerializer):
    """Minimal serializer for user lists."""
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'user_type', 'is_active']
