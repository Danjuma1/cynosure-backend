"""
Brief Connect models for Cynosure.
Peer-to-peer platform for lawyers to seek help holding briefs in court.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.common.models import BaseModel, TimeStampedModel


class BriefRequest(BaseModel):
    """
    A request posted by a lawyer seeking another lawyer to hold their brief
    or assist with any court task on a specific hearing date.
    """
    BRIEF_TYPE_CHOICES = [
        ('mention', 'Mention / Call Over'),
        ('argue_motion', 'Argue Motion'),
        ('full_appearance', 'Full Court Appearance'),
        ('file_process', 'File Court Process'),
        ('collect_certified_copy', 'Collect Certified Copy'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    requester = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='brief_requests_posted',
    )

    # Optional — links directly from a CSI cause list entry
    cause_list_entry = models.ForeignKey(
        'cause_lists.CauseListEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brief_requests',
    )
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brief_requests',
    )

    court = models.ForeignKey(
        'courts.Court',
        on_delete=models.CASCADE,
        related_name='brief_requests',
    )
    judge = models.ForeignKey(
        'judges.Judge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brief_requests',
    )

    hearing_date = models.DateField(db_index=True)

    # Matter details
    case_number = models.CharField(max_length=100, blank=True)
    parties = models.CharField(max_length=500, blank=True)
    brief_type = models.CharField(max_length=30, choices=BRIEF_TYPE_CHOICES)
    instructions = models.TextField()

    # Compensation
    offered_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fee_negotiable = models.BooleanField(default=True)

    # When the requester needs a confirmed lawyer by
    deadline = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)

    # Denormalized for fast listing queries
    application_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'hearing_date']),
            models.Index(fields=['court', 'hearing_date']),
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['hearing_date']),
        ]

    def __str__(self):
        return f"Brief Request by {self.requester.full_name} at {self.court.name} on {self.hearing_date}"

    def update_application_count(self):
        self.application_count = self.applications.filter(
            status__in=['pending', 'accepted'], is_deleted=False
        ).count()
        self.save(update_fields=['application_count'])


class BriefApplication(BaseModel):
    """
    An offer by a lawyer to assist with a brief request.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    brief_request = models.ForeignKey(
        BriefRequest,
        on_delete=models.CASCADE,
        related_name='applications',
    )
    applicant = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='brief_applications',
    )

    proposed_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['brief_request', 'applicant']
        indexes = [
            models.Index(fields=['brief_request', 'status']),
            models.Index(fields=['applicant', 'status']),
        ]

    def __str__(self):
        return f"{self.applicant.full_name} applied to {self.brief_request}"


class BriefEngagement(TimeStampedModel):
    """
    A confirmed engagement created when a requester accepts an application.
    Tracks the arrangement through to completion or dispute.
    """
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('disputed', 'Disputed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brief_request = models.OneToOneField(
        BriefRequest,
        on_delete=models.CASCADE,
        related_name='engagement',
    )
    holding_lawyer = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='engagements_as_holder',
    )
    requester = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='engagements_as_requester',
    )

    agreed_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed', db_index=True)

    outcome_notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['holding_lawyer', 'status']),
            models.Index(fields=['requester', 'status']),
        ]

    def __str__(self):
        return f"Engagement: {self.requester.full_name} ↔ {self.holding_lawyer.full_name}"


class BriefReview(TimeStampedModel):
    """
    A post-engagement review submitted by the requester about the holding lawyer.
    Builds a reputation layer for Brief Connect over time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engagement = models.OneToOneField(
        BriefEngagement,
        on_delete=models.CASCADE,
        related_name='review',
    )
    reviewer = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='reviews_given',
    )
    reviewee = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='reviews_received',
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reviewee']),
        ]

    def __str__(self):
        return f"Review by {self.reviewer.full_name} for {self.reviewee.full_name} — {self.rating}/5"
