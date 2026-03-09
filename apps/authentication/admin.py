"""
Admin configuration for authentication models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserFollowing, OTPCode, UserActivity, DeviceToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    list_display = [
        'email', 'full_name', 'user_type', 'is_active',
        'is_verified', 'date_joined',
    ]
    list_filter = ['user_type', 'is_active', 'is_verified', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'bar_number']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': (
                'first_name', 'last_name', 'title', 'phone_number',
                'profile_picture', 'bio',
            )
        }),
        ('Professional Info', {
            'fields': ('bar_number', 'year_of_call', 'specializations')
        }),
        ('Permissions', {
            'fields': (
                'user_type', 'is_active', 'is_staff', 'is_superuser',
                'is_verified', 'groups', 'user_permissions',
            )
        }),
        ('Notifications', {
            'fields': (
                'email_notifications', 'push_notifications',
                'sms_notifications',
            )
        }),
        ('Security', {
            'fields': (
                'two_factor_enabled', 'failed_login_attempts',
                'lockout_until', 'last_login_ip',
            )
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'verified_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'password1', 'password2',
                'user_type', 'is_active',
            ),
        }),
    )


@admin.register(UserFollowing)
class UserFollowingAdmin(admin.ModelAdmin):
    """Admin interface for UserFollowing model."""
    list_display = ['user', 'follow_type', 'object_id', 'notifications_enabled', 'created_at']
    list_filter = ['follow_type', 'notifications_enabled']
    search_fields = ['user__email']
    raw_id_fields = ['user']


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    """Admin interface for OTPCode model."""
    list_display = ['user', 'purpose', 'is_used', 'expires_at', 'created_at']
    list_filter = ['purpose', 'is_used']
    search_fields = ['user__email']
    raw_id_fields = ['user']
    readonly_fields = ['code']


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin interface for UserActivity model."""
    list_display = ['user', 'activity_type', 'ip_address', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__email']
    raw_id_fields = ['user']
    readonly_fields = ['user', 'activity_type', 'details', 'ip_address', 'user_agent', 'created_at']


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """Admin interface for DeviceToken model."""
    list_display = ['user', 'platform', 'device_name', 'is_active', 'last_used']
    list_filter = ['platform', 'is_active']
    search_fields = ['user__email', 'device_name']
    raw_id_fields = ['user']
