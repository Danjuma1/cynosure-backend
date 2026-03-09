"""
Judges models for Cynosure.
"""
import uuid
from django.db import models
from apps.common.models import BaseModel, TimeStampedModel


class Judge(BaseModel):
    """
    Represents a judge in the Nigerian judicial system.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('not_sitting', 'Not Sitting'),
        ('retired', 'Retired'),
        ('transferred', 'Transferred'),
        ('suspended', 'Suspended'),
    ]
    
    TITLE_CHOICES = [
        ('HON', 'Honourable'),
        ('HON_JUSTICE', 'Honourable Justice'),
        ('JUSTICE', 'Justice'),
        ('HIS_LORDSHIP', 'His Lordship'),
        ('HER_LADYSHIP', 'Her Ladyship'),
        ('CHIEF_JUDGE', 'Chief Judge'),
        ('PRESIDENT', 'President'),
        ('GRAND_KADI', 'Grand Kadi'),
    ]
    
    # Basic information
    title = models.CharField(max_length=20, choices=TITLE_CHOICES, default='HON_JUSTICE')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=100, blank=True)
    
    # Professional details
    court = models.ForeignKey(
        'courts.Court',
        on_delete=models.PROTECT,
        related_name='judges'
    )
    division = models.ForeignKey(
        'courts.Division',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='judges'
    )
    
    # Status and availability
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    status_note = models.TextField(blank=True, help_text="Reason for current status")
    status_effective_from = models.DateField(null=True, blank=True)
    status_effective_until = models.DateField(null=True, blank=True)
    
    # Contact
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    office_location = models.CharField(max_length=255, blank=True)
    
    # Profile
    photo = models.ImageField(upload_to='judges/photos/', null=True, blank=True)
    biography = models.TextField(blank=True)
    appointment_date = models.DateField(null=True, blank=True)
    year_of_call = models.PositiveIntegerField(null=True, blank=True)
    
    # Qualifications and expertise
    qualifications = models.JSONField(default=list, blank=True)
    areas_of_expertise = models.JSONField(default=list, blank=True)
    previous_positions = models.JSONField(default=list, blank=True)
    
    # Courtroom assignment
    default_courtroom = models.ForeignKey(
        'courts.Courtroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_judges'
    )
    
    # Sitting schedule
    sitting_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Default sitting days [0=Monday, 4=Friday]"
    )
    sitting_time_start = models.TimeField(null=True, blank=True)
    sitting_time_end = models.TimeField(null=True, blank=True)
    
    # Statistics (cached/computed)
    total_cases = models.PositiveIntegerField(default=0)
    pending_cases = models.PositiveIntegerField(default=0)
    follower_count = models.PositiveIntegerField(default=0)
    
    # Flags
    is_chief_judge = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['court', 'status']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['last_name', 'first_name']),
        ]
    
    def __str__(self):
        return f"{self.get_title_display()} {self.full_name}"
    
    @property
    def full_name(self):
        """Get judge's full name."""
        names = [self.first_name]
        if self.other_names:
            names.append(self.other_names)
        names.append(self.last_name)
        return ' '.join(names)
    
    @property
    def formal_name(self):
        """Get judge's formal name with title."""
        return f"{self.get_title_display()} {self.full_name}"
    
    def is_available(self):
        """Check if judge is currently available for cases."""
        return self.status == 'active' and self.is_active


class JudgeAvailability(TimeStampedModel):
    """
    Track judge availability for specific dates.
    Overrides default sitting schedule.
    """
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('not_sitting', 'Not Sitting'),
        ('on_leave', 'On Leave'),
        ('conference', 'Conference/Meeting'),
        ('training', 'Training'),
        ('special_assignment', 'Special Assignment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE, related_name='availability_records')
    
    date = models.DateField(db_index=True)
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES)
    reason = models.TextField(blank=True)
    
    # Time override (if partially available)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # Alternate arrangements
    alternate_judge = models.ForeignKey(
        Judge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acting_for'
    )
    alternate_courtroom = models.ForeignKey(
        'courts.Courtroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_availability_records'
    )
    
    class Meta:
        ordering = ['-date']
        unique_together = ['judge', 'date']
        indexes = [
            models.Index(fields=['judge', 'date']),
            models.Index(fields=['date', 'availability']),
        ]
    
    def __str__(self):
        return f"{self.judge.full_name} - {self.date} - {self.get_availability_display()}"


class JudgeTransfer(TimeStampedModel):
    """
    Track judge transfers between courts/divisions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE, related_name='transfers')
    
    # Previous assignment
    from_court = models.ForeignKey(
        'courts.Court',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_out'
    )
    from_division = models.ForeignKey(
        'courts.Division',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_out'
    )
    
    # New assignment
    to_court = models.ForeignKey(
        'courts.Court',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_in'
    )
    to_division = models.ForeignKey(
        'courts.Division',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_in'
    )
    
    effective_date = models.DateField()
    reason = models.TextField(blank=True)
    transfer_order_reference = models.CharField(max_length=100, blank=True)
    
    created_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        ordering = ['-effective_date']
    
    def __str__(self):
        return f"{self.judge.full_name} transfer on {self.effective_date}"


class JudgeLeave(TimeStampedModel):
    """
    Track judge leave periods.
    """
    LEAVE_TYPE_CHOICES = [
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('maternity', 'Maternity Leave'),
        ('study', 'Study Leave'),
        ('sabbatical', 'Sabbatical'),
        ('special', 'Special Leave'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE, related_name='leave_records')
    
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    
    # Approval
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Acting judge
    acting_judge = models.ForeignKey(
        Judge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acting_periods'
    )
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['judge', 'start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.judge.full_name} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"


class JudgeRating(TimeStampedModel):
    """
    Anonymous ratings/feedback for judges (optional feature).
    """
    RATING_CRITERIA = [
        ('punctuality', 'Punctuality'),
        ('professionalism', 'Professionalism'),
        ('knowledge', 'Legal Knowledge'),
        ('fairness', 'Fairness'),
        ('efficiency', 'Case Management Efficiency'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE, related_name='ratings')
    
    criteria = models.CharField(max_length=20, choices=RATING_CRITERIA)
    rating = models.PositiveSmallIntegerField()  # 1-5
    comment = models.TextField(blank=True)
    
    # Anonymous but linked to user for abuse prevention
    rated_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True
    )
    
    is_verified = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['judge', 'criteria']),
        ]
    
    def __str__(self):
        return f"{self.judge.full_name} - {self.get_criteria_display()}: {self.rating}"
