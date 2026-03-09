"""
Authentication models for Cynosure.
Custom User model with role-based access control.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class UserManager(BaseUserManager):
    """Custom user manager for User model."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'super_admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Custom User model for Cynosure.
    Uses email as the unique identifier.
    """
    USER_TYPE_CHOICES = [
        ('lawyer', 'Lawyer'),
        ('firm_admin', 'Law Firm Admin'),
        ('registry_staff', 'Registry Staff'),
        ('super_admin', 'Super Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Profile fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(max_length=50, blank=True)  # e.g., "Esq.", "SAN"
    
    # Role and permissions
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='lawyer')
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Profile details
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bar_number = models.CharField(max_length=50, blank=True)  # For lawyers
    year_of_call = models.PositiveIntegerField(null=True, blank=True)
    specializations = models.JSONField(default=list, blank=True)
    bio = models.TextField(blank=True)
    
    # Settings
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Security
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    
    # 2FA
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['bar_number']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    @property
    def full_name(self):
        """Return user's full name."""
        name = f"{self.first_name} {self.last_name}"
        if self.title:
            name = f"{name}, {self.title}"
        return name.strip()
    
    def is_locked(self):
        """Check if account is locked."""
        if self.lockout_until and self.lockout_until > timezone.now():
            return True
        return False
    
    def reset_failed_attempts(self):
        """Reset failed login attempts."""
        self.failed_login_attempts = 0
        self.lockout_until = None
        self.save(update_fields=['failed_login_attempts', 'lockout_until'])
    
    def increment_failed_attempts(self, max_attempts=5, lockout_minutes=30):
        """Increment failed login attempts and lock if needed."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.lockout_until = timezone.now() + timezone.timedelta(minutes=lockout_minutes)
        self.save(update_fields=['failed_login_attempts', 'lockout_until'])


class UserFollowing(TimeStampedModel):
    """
    Track what courts, judges, cases, and categories a user follows.
    """
    FOLLOW_TYPE_CHOICES = [
        ('court', 'Court'),
        ('judge', 'Judge'),
        ('case', 'Case'),
        ('category', 'Category'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followings')
    follow_type = models.CharField(max_length=20, choices=FOLLOW_TYPE_CHOICES)
    object_id = models.UUIDField(db_index=True)  # ID of the followed entity
    notifications_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'follow_type', 'object_id']
        indexes = [
            models.Index(fields=['user', 'follow_type']),
            models.Index(fields=['follow_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} follows {self.follow_type}:{self.object_id}"


class OTPCode(TimeStampedModel):
    """
    OTP codes for password reset and email verification.
    """
    PURPOSE_CHOICES = [
        ('password_reset', 'Password Reset'),
        ('email_verification', 'Email Verification'),
        ('phone_verification', 'Phone Verification'),
        ('two_factor', 'Two Factor Authentication'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=10)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'purpose', 'is_used']),
            models.Index(fields=['code', 'is_used']),
        ]
    
    def __str__(self):
        return f"OTP for {self.user.email} - {self.purpose}"
    
    def is_valid(self):
        """Check if OTP is still valid."""
        return (
            not self.is_used and 
            self.expires_at > timezone.now() and
            self.attempts < 5
        )
    
    def mark_used(self):
        """Mark OTP as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class UserActivity(TimeStampedModel):
    """
    Track user activity for analytics and security.
    """
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('profile_update', 'Profile Update'),
        ('search', 'Search'),
        ('view_case', 'View Case'),
        ('view_cause_list', 'View Cause List'),
        ('follow', 'Follow'),
        ('unfollow', 'Unfollow'),
        ('download', 'Download'),
        ('filing', 'Filing'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'User activities'
        indexes = [
            models.Index(fields=['user', 'activity_type']),
            models.Index(fields=['activity_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.activity_type}"


class DeviceToken(TimeStampedModel):
    """
    Store device tokens for push notifications.
    """
    PLATFORM_CHOICES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.TextField()
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    device_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'token']
        indexes = [
            models.Index(fields=['user', 'platform', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.platform}"
