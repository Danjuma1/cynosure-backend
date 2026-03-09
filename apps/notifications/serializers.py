"""
Serializers for notifications endpoints.
"""
from rest_framework import serializers
from .models import Notification, NotificationPreference, WebPushSubscription


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'notification_type_display',
            'title', 'message', 'priority', 'priority_display',
            'category', 'action_url',
            'court_id', 'judge_id', 'case_id', 'cause_list_id',
            'is_read', 'read_at', 'is_archived', 'archived_at',
            'data', 'created_at',
        ]
        read_only_fields = fields


class NotificationListSerializer(serializers.ModelSerializer):
    """Minimal serializer for notification listings."""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'priority', 'is_read', 'created_at',
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'push_enabled', 'sms_enabled',
            'cause_list_new', 'cause_list_update', 'cause_list_status',
            'case_adjournment', 'not_sitting', 'time_change',
            'courtroom_change', 'case_update', 'case_on_docket',
            'judge_status', 'filing_update', 'reminder',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'daily_digest', 'digest_time',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class WebPushSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for web push subscriptions."""
    
    class Meta:
        model = WebPushSubscription
        fields = ['id', 'endpoint', 'p256dh', 'auth', 'browser', 'device', 'is_active']
        read_only_fields = ['id']


class MarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read."""
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    mark_all = serializers.BooleanField(default=False)


class NotificationCountSerializer(serializers.Serializer):
    """Serializer for notification counts."""
    total = serializers.IntegerField()
    unread = serializers.IntegerField()
    by_type = serializers.DictField()
