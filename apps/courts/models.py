"""
Courts models for Cynosure.
Nigerian court hierarchy and organization.
"""
import uuid
from django.db import models
from apps.common.models import BaseModel, TimeStampedModel


class Court(BaseModel):
    """
    Represents a court in the Nigerian judicial system.
    """
    COURT_TYPE_CHOICES = [
        ('SC', 'Supreme Court'),
        ('CA', 'Court of Appeal'),
        ('FHC', 'Federal High Court'),
        ('NIC', 'National Industrial Court'),
        ('SHC', 'State High Court'),
        ('FCT', 'FCT High Court'),
        ('SAC', 'Sharia Court of Appeal'),
        ('CCA', 'Customary Court of Appeal'),
        ('MC', 'Magistrate Court'),
        ('AC', 'Area Court'),
        ('CC', 'Customary Court'),
    ]
    
    STATE_CHOICES = [
        ('AB', 'Abia'), ('AD', 'Adamawa'), ('AK', 'Akwa Ibom'),
        ('AN', 'Anambra'), ('BA', 'Bauchi'), ('BY', 'Bayelsa'),
        ('BE', 'Benue'), ('BO', 'Borno'), ('CR', 'Cross River'),
        ('DE', 'Delta'), ('EB', 'Ebonyi'), ('ED', 'Edo'),
        ('EK', 'Ekiti'), ('EN', 'Enugu'), ('FC', 'FCT Abuja'),
        ('GO', 'Gombe'), ('IM', 'Imo'), ('JI', 'Jigawa'),
        ('KD', 'Kaduna'), ('KN', 'Kano'), ('KT', 'Katsina'),
        ('KE', 'Kebbi'), ('KO', 'Kogi'), ('KW', 'Kwara'),
        ('LA', 'Lagos'), ('NA', 'Nasarawa'), ('NI', 'Niger'),
        ('OG', 'Ogun'), ('ON', 'Ondo'), ('OS', 'Osun'),
        ('OY', 'Oyo'), ('PL', 'Plateau'), ('RI', 'Rivers'),
        ('SO', 'Sokoto'), ('TA', 'Taraba'), ('YO', 'Yobe'),
        ('ZA', 'Zamfara'),
    ]
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    court_type = models.CharField(max_length=5, choices=COURT_TYPE_CHOICES, db_index=True)
    state = models.CharField(max_length=3, choices=STATE_CHOICES, db_index=True)
    
    # Location details
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Contact information
    phone_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Jurisdiction
    jurisdiction = models.TextField(blank=True, help_text="Description of court's jurisdiction")
    jurisdiction_areas = models.JSONField(default=list, blank=True)
    
    # Court details
    description = models.TextField(blank=True)
    established_date = models.DateField(null=True, blank=True)
    chief_judge_id = models.UUIDField(null=True, blank=True)  # Reference to Judge
    
    # Metadata
    is_active = models.BooleanField(default=True)
    working_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Days court is in session [0=Monday, 4=Friday]"
    )
    working_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text="Working hours {start: '08:00', end: '16:00'}"
    )
    
    # Statistics (cached/computed)
    total_judges = models.PositiveIntegerField(default=0)
    total_divisions = models.PositiveIntegerField(default=0)
    follower_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['court_type', 'state']),
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_court_type_display()})"
    
    @property
    def full_address(self):
        """Get formatted full address."""
        parts = [self.address, self.city, self.get_state_display()]
        return ', '.join(p for p in parts if p)


class Division(BaseModel):
    """
    Represents a division within a court.
    E.g., Criminal Division, Civil Division, Family Division
    """
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='divisions')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, db_index=True)
    description = models.TextField(blank=True)
    
    # Location within court
    building = models.CharField(max_length=100, blank=True)
    floor = models.CharField(max_length=50, blank=True)
    
    # Contact
    phone_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    head_judge_id = models.UUIDField(null=True, blank=True)
    
    # Statistics
    total_judges = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['name']
        unique_together = ['court', 'code']
        indexes = [
            models.Index(fields=['court', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.court.name}"


class Courtroom(BaseModel):
    """
    Represents a physical courtroom.
    """
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='courtrooms')
    division = models.ForeignKey(
        Division, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='courtrooms'
    )
    
    name = models.CharField(max_length=100)  # e.g., "Courtroom 1", "Court A"
    number = models.CharField(max_length=20, blank=True)
    
    # Location
    building = models.CharField(max_length=100, blank=True)
    floor = models.CharField(max_length=50, blank=True)
    
    # Capacity and facilities
    capacity = models.PositiveIntegerField(null=True, blank=True)
    has_video_conferencing = models.BooleanField(default=False)
    has_recording = models.BooleanField(default=False)
    is_accessible = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['court', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.court.name}"


class Panel(BaseModel):
    """
    Represents a panel of judges (for Appeal Courts).
    """
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='panels')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, db_index=True)
    
    # Panel composition
    presiding_judge_id = models.UUIDField(null=True, blank=True)
    member_ids = models.JSONField(default=list, blank=True)  # List of judge UUIDs
    
    # Status
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    
    # Assigned matters
    assigned_categories = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['court', 'code']
    
    def __str__(self):
        return f"{self.name} - {self.court.name}"


class CourtRule(BaseModel):
    """
    Court rules and practice directions.
    """
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='rules')
    
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=50, choices=[
        ('rule', 'Court Rule'),
        ('practice_direction', 'Practice Direction'),
        ('circular', 'Circular'),
        ('notice', 'Notice'),
        ('guideline', 'Guideline'),
    ])
    
    # File
    document = models.FileField(upload_to='court_rules/')
    file_size = models.PositiveIntegerField(default=0)
    
    # Dates
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Status
    is_current = models.BooleanField(default=True)
    supersedes = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='superseded_by'
    )
    
    class Meta:
        ordering = ['-effective_date', 'title']
    
    def __str__(self):
        return f"{self.title} - {self.court.name}"


class CourtHoliday(TimeStampedModel):
    """
    Court holidays and vacation periods.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='holidays')
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    holiday_type = models.CharField(max_length=50, choices=[
        ('public', 'Public Holiday'),
        ('vacation', 'Court Vacation'),
        ('special', 'Special Holiday'),
    ])
    
    is_recurring = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"


class CourtContact(TimeStampedModel):
    """
    Additional contact information for courts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='contacts')
    
    contact_type = models.CharField(max_length=50, choices=[
        ('registrar', 'Registrar'),
        ('chief_registrar', 'Chief Registrar'),
        ('deputy_registrar', 'Deputy Registrar'),
        ('information', 'Information Desk'),
        ('filing', 'Filing Office'),
        ('records', 'Records Office'),
        ('accounts', 'Accounts'),
        ('other', 'Other'),
    ])
    
    name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    office_location = models.CharField(max_length=255, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['contact_type', 'name']
    
    def __str__(self):
        return f"{self.get_contact_type_display()} - {self.court.name}"
