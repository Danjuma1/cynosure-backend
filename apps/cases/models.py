"""
Cases models for Cynosure.
Case tracking and history management.
"""
import uuid
from django.db import models
from apps.common.models import BaseModel, TimeStampedModel


class Case(BaseModel):
    """
    Represents a legal case in the Nigerian court system.
    """
    CASE_TYPE_CHOICES = [
        ('civil', 'Civil'),
        ('criminal', 'Criminal'),
        ('appeal', 'Appeal'),
        ('constitutional', 'Constitutional'),
        ('commercial', 'Commercial'),
        ('family', 'Family'),
        ('probate', 'Probate'),
        ('land', 'Land'),
        ('admiralty', 'Admiralty'),
        ('election', 'Election Petition'),
        ('tax', 'Tax'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('adjourned', 'Adjourned'),
        ('reserved', 'Reserved for Judgment'),
        ('judgment', 'Judgment Delivered'),
        ('settled', 'Settled'),
        ('withdrawn', 'Withdrawn'),
        ('struck_out', 'Struck Out'),
        ('dismissed', 'Dismissed'),
        ('transferred', 'Transferred'),
        ('appealed', 'Appealed'),
        ('concluded', 'Concluded'),
    ]
    
    # Case identification
    case_number = models.CharField(max_length=100, unique=True, db_index=True)
    suit_number = models.CharField(max_length=100, blank=True, db_index=True)
    old_case_numbers = models.JSONField(default=list, blank=True)  # For transferred cases
    
    # Court and judge
    court = models.ForeignKey(
        'courts.Court',
        on_delete=models.PROTECT,
        related_name='cases'
    )
    division = models.ForeignKey(
        'courts.Division',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cases'
    )
    judge = models.ForeignKey(
        'judges.Judge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cases'
    )
    
    # Parties
    parties = models.TextField(help_text="Full party description")
    applicant = models.CharField(max_length=500, blank=True)
    respondent = models.CharField(max_length=500, blank=True)
    
    # Additional parties
    co_applicants = models.JSONField(default=list, blank=True)
    co_respondents = models.JSONField(default=list, blank=True)
    interested_parties = models.JSONField(default=list, blank=True)
    
    # Case details
    case_type = models.CharField(max_length=20, choices=CASE_TYPE_CHOICES, db_index=True)
    matter_type = models.CharField(max_length=100, blank=True)
    subject_matter = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    status_note = models.TextField(blank=True)
    
    # Dates
    filing_date = models.DateField(null=True, blank=True)
    first_hearing_date = models.DateField(null=True, blank=True)
    last_hearing_date = models.DateField(null=True, blank=True)
    next_hearing_date = models.DateField(null=True, blank=True)
    judgment_date = models.DateField(null=True, blank=True)
    
    # Outcome
    judgment_summary = models.TextField(blank=True)
    ruling = models.TextField(blank=True)
    
    # Counsel
    counsel_for_applicant = models.TextField(blank=True)
    counsel_for_respondent = models.TextField(blank=True)
    
    # Statistics
    total_adjournments = models.PositiveIntegerField(default=0)
    total_hearings = models.PositiveIntegerField(default=0)
    follower_count = models.PositiveIntegerField(default=0)
    
    # Source tracking
    source = models.CharField(max_length=50, choices=[
        ('manual', 'Manual Entry'),
        ('scraper', 'Web Scraper'),
        ('cause_list', 'Cause List'),
        ('filing', 'E-Filing'),
        ('import', 'Data Import'),
    ], default='manual')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['case_number']),
            models.Index(fields=['court', 'status']),
            models.Index(fields=['judge', 'status']),
            models.Index(fields=['next_hearing_date']),
            models.Index(fields=['case_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.case_number} - {self.parties[:50]}"


class CaseHearing(TimeStampedModel):
    """
    Record of individual case hearings.
    """
    OUTCOME_CHOICES = [
        ('adjourned', 'Adjourned'),
        ('hearing', 'Hearing Held'),
        ('ruling', 'Ruling Delivered'),
        ('judgment', 'Judgment Delivered'),
        ('struck_out', 'Struck Out'),
        ('settled', 'Settled'),
        ('withdrawn', 'Withdrawn'),
        ('dismissed', 'Dismissed'),
        ('mention', 'Mention'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='hearings')
    
    # Hearing details
    date = models.DateField(db_index=True)
    time = models.TimeField(null=True, blank=True)
    
    # Judge (may be different from case judge)
    judge = models.ForeignKey(
        'judges.Judge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hearings'
    )
    
    # Location
    courtroom = models.CharField(max_length=100, blank=True)
    
    # Outcome
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default='adjourned')
    outcome_notes = models.TextField(blank=True)
    
    # Next date
    next_date = models.DateField(null=True, blank=True)
    adjournment_reason = models.TextField(blank=True)
    
    # Attendance
    applicant_present = models.BooleanField(null=True)
    respondent_present = models.BooleanField(null=True)
    counsel_applicant_present = models.BooleanField(null=True)
    counsel_respondent_present = models.BooleanField(null=True)
    
    # Notes
    proceedings = models.TextField(blank=True)
    orders = models.TextField(blank=True)
    
    # Source
    cause_list_entry = models.ForeignKey(
        'cause_lists.CauseListEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hearing_records'
    )
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['case', 'date']),
            models.Index(fields=['date', 'outcome']),
        ]
    
    def __str__(self):
        return f"{self.case.case_number} - {self.date}"


class CaseDocument(BaseModel):
    """
    Documents associated with a case.
    """
    DOCUMENT_TYPE_CHOICES = [
        ('originating', 'Originating Process'),
        ('statement_of_claim', 'Statement of Claim'),
        ('statement_of_defence', 'Statement of Defence'),
        ('motion', 'Motion'),
        ('affidavit', 'Affidavit'),
        ('exhibit', 'Exhibit'),
        ('ruling', 'Ruling'),
        ('judgment', 'Judgment'),
        ('order', 'Order'),
        ('brief', 'Brief'),
        ('other', 'Other'),
    ]
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='documents')
    
    title = models.CharField(max_length=500)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    
    # File
    file = models.FileField(upload_to='case_documents/')
    file_size = models.PositiveIntegerField(default=0)
    file_type = models.CharField(max_length=50, blank=True)
    
    # Metadata
    filing_date = models.DateField(null=True, blank=True)
    filed_by = models.CharField(max_length=255, blank=True)
    
    # Visibility
    is_public = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-filing_date', '-created_at']
    
    def __str__(self):
        return f"{self.case.case_number} - {self.title}"


class CaseNote(TimeStampedModel):
    """
    User notes on cases.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='case_notes'
    )
    
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    
    # Privacy
    is_private = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.case.case_number} - Note by {self.user.email}"


class CaseTimeline(TimeStampedModel):
    """
    Timeline of events for a case.
    Auto-generated from hearings and status changes.
    """
    EVENT_TYPE_CHOICES = [
        ('filed', 'Case Filed'),
        ('hearing', 'Hearing'),
        ('adjournment', 'Adjournment'),
        ('ruling', 'Ruling'),
        ('judgment', 'Judgment'),
        ('status_change', 'Status Change'),
        ('transfer', 'Transfer'),
        ('document', 'Document Filed'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='timeline')
    
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    event_date = models.DateTimeField()
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Related objects
    hearing = models.ForeignKey(
        CaseHearing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    document = models.ForeignKey(
        CaseDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-event_date']
        indexes = [
            models.Index(fields=['case', 'event_date']),
        ]
    
    def __str__(self):
        return f"{self.case.case_number} - {self.title}"


class CaseTransfer(TimeStampedModel):
    """
    Track case transfers between courts/judges.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='transfers')
    
    # Previous assignment
    from_court = models.ForeignKey(
        'courts.Court',
        on_delete=models.SET_NULL,
        null=True,
        related_name='cases_transferred_out'
    )
    from_judge = models.ForeignKey(
        'judges.Judge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cases_transferred_out'
    )
    
    # New assignment
    to_court = models.ForeignKey(
        'courts.Court',
        on_delete=models.SET_NULL,
        null=True,
        related_name='cases_transferred_in'
    )
    to_judge = models.ForeignKey(
        'judges.Judge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cases_transferred_in'
    )
    
    transfer_date = models.DateField()
    reason = models.TextField(blank=True)
    order_reference = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-transfer_date']
    
    def __str__(self):
        return f"{self.case.case_number} transfer on {self.transfer_date}"
