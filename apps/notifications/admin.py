from django.contrib import admin
from .models import Notification, NotificationBatch, NotificationPreference, WebPushSubscription, EmailTemplate

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'is_archived']
    search_fields = ['user__email', 'title']

@admin.register(NotificationBatch)
class NotificationBatchAdmin(admin.ModelAdmin):
    list_display = ['notification_type', 'title', 'status', 'total_recipients', 'sent_count']
    list_filter = ['status', 'notification_type']
    search_fields = ['title']

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'push_enabled', 'sms_enabled']
    list_filter = ['email_enabled', 'push_enabled', 'sms_enabled']
    search_fields = ['user__email']

@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'browser', 'device', 'is_active']
    list_filter = ['browser', 'is_active']
    search_fields = ['user__email']

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active']
    list_filter = ['notification_type', 'is_active']
    search_fields = ['name', 'subject']