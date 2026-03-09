"""
Notifications models for Cynosure.
Multi-channel notification system.
"""
import uuid
from django.db import models
from apps.common.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    Individual notification record.
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('cause_list_new', 'New Cause List'),
        ('cause_list_update', 'Cause List Updated'),
        ('cause_list_status', 'Cause List Status Change'),
        ('case_adjournment', 'Case Adjourned'),
        ('not_sitting', 'Not Sitting Notice'),
        ('time_change', 'Time Changed'),
        ('courtroom_change', 'Courtroom Changed'),
        ('case_update', 'Case Update'),
        ('case_on_docket', 'Case on Docket'),
        ('judge_status', 'Judge Status Change'),
        ('filing_update', 'Filing Update'),
        ('filing_approved', 'Filing Approved'),
        ('filing_rejected', 'Filing Rejected'),
        ('reminder', 'Reminder'),
        ('system', 'System Notification'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification content
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Priority and categorization
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    category = models.CharField(max_length=50, blank=True)
    
    # Related objects
    court_id = models.UUIDField(null=True, blank=True, db_index=True)
    judge_id = models.UUIDField(null=True, blank=True, db_index=True)
    case_id = models.UUIDField(null=True, blank=True, db_index=True)
    cause_list_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Action URL
    action_url = models.CharField(max_length=500, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    push_sent = models.BooleanField(default=False)
    push_sent_at = models.DateTimeField(null=True, blank=True)
    websocket_sent = models.BooleanField(default=False)
    websocket_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'is_archived']),
            models.Index(fields=['user', 'notification_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['court_id']),
            models.Index(fields=['judge_id']),
            models.Index(fields=['case_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"
    
    def mark_read(self):
        """Mark notification as read."""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
    
    def archive(self):
        """Archive notification."""
        from django.utils import timezone
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=['is_archived', 'archived_at'])


class NotificationBatch(TimeStampedModel):
    """
    Batch of notifications for bulk processing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Batch info
    notification_type = models.CharField(max_length=30)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Targeting
    target_court_id = models.UUIDField(null=True, blank=True)
    target_judge_id = models.UUIDField(null=True, blank=True)
    target_case_id = models.UUIDField(null=True, blank=True)
    
    # Processing status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Additional data
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Batch {self.id} - {self.notification_type}"


class NotificationPreference(TimeStampedModel):
    """
    User notification preferences.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Global settings
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    
    # Per-type preferences
    cause_list_new = models.BooleanField(default=True)
    cause_list_update = models.BooleanField(default=True)
    cause_list_status = models.BooleanField(default=True)
    case_adjournment = models.BooleanField(default=True)
    not_sitting = models.BooleanField(default=True)
    time_change = models.BooleanField(default=True)
    courtroom_change = models.BooleanField(default=True)
    case_update = models.BooleanField(default=True)
    case_on_docket = models.BooleanField(default=True)
    judge_status = models.BooleanField(default=True)
    filing_update = models.BooleanField(default=True)
    reminder = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    # Digest settings
    daily_digest = models.BooleanField(default=False)
    digest_time = models.TimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Notification preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.email}"


class WebPushSubscription(TimeStampedModel):
    """
    Web push subscription for browser notifications.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='webpush_subscriptions'
    )
    
    endpoint = models.TextField()
    p256dh = models.CharField(max_length=500)
    auth = models.CharField(max_length=500)
    
    browser = models.CharField(max_length=100, blank=True)
    device = models.CharField(max_length=100, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'endpoint']
    
    def __str__(self):
        return f"WebPush for {self.user.email}"


class EmailTemplate(TimeStampedModel):
    """
    Email templates for notifications.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, unique=True)
    notification_type = models.CharField(max_length=30)
    
    subject = models.CharField(max_length=255)
    html_body = models.TextField()
    text_body = models.TextField()
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
