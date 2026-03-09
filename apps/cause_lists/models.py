"""
Cause Lists models for Cynosure.
This is the core module for daily court schedules.
"""
import uuid
from django.db import models
from apps.common.models import BaseModel, TimeStampedModel


class CauseList(BaseModel):
    """
    Represents a cause list (daily court schedule) for a judge.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('sitting', 'Sitting'),
        ('adjourned', 'Adjourned'),
        ('not_sitting', 'Not Sitting'),
        ('risen', 'Risen'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Core fields
    court = models.ForeignKey(
        'courts.Court',
        on_delete=models.CASCADE,
        related_name='cause_lists'
    )
    judge = models.ForeignKey(
        'judges.Judge',
        on_delete=models.CASCADE,
        related_name='cause_lists',
        null=True,
        blank=True
    )
    panel = models.ForeignKey(
        'courts.Panel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cause_lists'
    )
    
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    
    # Courtroom
    courtroom = models.ForeignKey(
        'courts.Courtroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cause_lists'
    )
    
    # Time
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # Status notes
    status_note = models.TextField(blank=True)
    adjournment_reason = models.TextField(blank=True)
    not_sitting_reason = models.TextField(blank=True)
    
    # PDF attachment
    pdf_file = models.FileField(upload_to='cause_lists/pdfs/', null=True, blank=True)
    pdf_file_size = models.PositiveIntegerField(default=0)
    pdf_uploaded_at = models.DateTimeField(null=True, blank=True)
    
    # Source tracking
    source = models.CharField(max_length=50, choices=[
        ('manual', 'Manual Entry'),
        ('upload', 'PDF Upload'),
        ('scraper', 'Web Scraper'),
        ('api', 'API Import'),
    ], default='manual')
    source_url = models.URLField(blank=True)
    
    # Metadata
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_cause_lists'
    )
    
    # Statistics
    total_cases = models.PositiveIntegerField(default=0)
    
    # Version tracking for changes
    version = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['-date', 'court__name']
        unique_together = ['court', 'judge', 'date']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['court', 'date']),
            models.Index(fields=['judge', 'date']),
            models.Index(fields=['status', 'date']),
        ]
    
    def __str__(self):
        judge_name = self.judge.full_name if self.judge else self.panel.name if self.panel else 'Unknown'
        return f"Cause List - {self.court.name} - {judge_name} - {self.date}"
    
    def update_case_count(self):
        """Update total cases count."""
        self.total_cases = self.entries.filter(is_deleted=False).count()
        self.save(update_fields=['total_cases'])


class CauseListEntry(BaseModel):
    """
    Individual case entry in a cause list.
    """
    cause_list = models.ForeignKey(
        CauseList,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cause_list_entries'
    )
    
    # Case identification
    case_number = models.CharField(max_length=100, db_index=True)
    suit_number = models.CharField(max_length=100, blank=True)
    
    # Parties
    parties = models.TextField(help_text="Full party names as they appear on the list")
    applicant = models.CharField(max_length=500, blank=True)
    respondent = models.CharField(max_length=500, blank=True)
    
    # Case details
    matter_type = models.CharField(max_length=100, blank=True)
    case_type = models.CharField(max_length=50, choices=[
        ('civil', 'Civil'),
        ('criminal', 'Criminal'),
        ('appeal', 'Appeal'),
        ('motion', 'Motion'),
        ('ruling', 'Ruling'),
        ('judgment', 'Judgment'),
        ('mention', 'Mention'),
        ('hearing', 'Hearing'),
        ('other', 'Other'),
    ], default='civil')
    
    # Schedule
    order_number = models.PositiveIntegerField(default=0, help_text="Order of appearance")
    scheduled_time = models.TimeField(null=True, blank=True)
    courtroom = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(max_length=50, choices=[
        ('scheduled', 'Scheduled'),
        ('called', 'Called'),
        ('in_progress', 'In Progress'),
        ('adjourned', 'Adjourned'),
        ('struck_out', 'Struck Out'),
        ('settled', 'Settled'),
        ('judgment', 'Judgment Delivered'),
        ('ruling', 'Ruling Delivered'),
        ('completed', 'Completed'),
    ], default='scheduled')
    
    # Outcome
    outcome = models.TextField(blank=True)
    next_date = models.DateField(null=True, blank=True)
    adjournment_reason = models.TextField(blank=True)
    
    # Counsel
    counsel_for_applicant = models.TextField(blank=True)
    counsel_for_respondent = models.TextField(blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order_number', 'scheduled_time']
        indexes = [
            models.Index(fields=['cause_list', 'order_number']),
            models.Index(fields=['case_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.case_number} - {self.parties[:50]}"


class CauseListChange(TimeStampedModel):
    """
    Track changes to cause lists for audit and notifications.
    """
    CHANGE_TYPE_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('status_changed', 'Status Changed'),
        ('time_changed', 'Time Changed'),
        ('courtroom_changed', 'Courtroom Changed'),
        ('case_added', 'Case Added'),
        ('case_removed', 'Case Removed'),
        ('case_reordered', 'Case Reordered'),
        ('adjourned', 'Adjourned'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cause_list = models.ForeignKey(
        CauseList,
        on_delete=models.CASCADE,
        related_name='changes'
    )
    entry = models.ForeignKey(
        CauseListEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='changes'
    )
    
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPE_CHOICES)
    
    # Change details
    field_name = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    
    # Full change record
    changes = models.JSONField(default=dict, blank=True)
    
    # Who made the change
    changed_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='cause_list_changes'
    )
    
    # Notification tracking
    notifications_sent = models.BooleanField(default=False)
    notifications_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cause_list', 'change_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.cause_list} - {self.get_change_type_display()}"


class CauseListSubscription(TimeStampedModel):
    """
    User subscriptions for cause list notifications.
    Allows granular notification preferences.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='cause_list_subscriptions'
    )
    
    # What to subscribe to
    court = models.ForeignKey(
        'courts.Court',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cause_list_subscribers'
    )
    judge = models.ForeignKey(
        'judges.Judge',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cause_list_subscribers'
    )
    case_number = models.CharField(max_length=100, blank=True)
    
    # Notification preferences
    notify_new_list = models.BooleanField(default=True)
    notify_changes = models.BooleanField(default=True)
    notify_status_change = models.BooleanField(default=True)
    notify_adjournment = models.BooleanField(default=True)
    
    # Channels
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['court', 'is_active']),
            models.Index(fields=['judge', 'is_active']),
        ]
    
    def __str__(self):
        target = self.court or self.judge or self.case_number or 'All'
        return f"{self.user.email} -> {target}"


class CauseListTemplate(BaseModel):
    """
    Templates for cause list parsing from different courts.
    Used by scrapers to handle varying formats.
    """
    court = models.ForeignKey(
        'courts.Court',
        on_delete=models.CASCADE,
        related_name='cause_list_templates'
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Parsing configuration
    file_type = models.CharField(max_length=20, choices=[
        ('pdf', 'PDF'),
        ('html', 'HTML'),
        ('docx', 'Word Document'),
        ('xlsx', 'Excel'),
    ], default='pdf')
    
    # Parsing rules (JSON configuration)
    parsing_rules = models.JSONField(default=dict)
    
    # Field mappings
    field_mappings = models.JSONField(default=dict)
    
    # Regular expressions for extraction
    regex_patterns = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['court__name', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.court.name}"
