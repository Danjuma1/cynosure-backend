"""
Structured dispute resolution for Brief Connect engagements. Opened when a
requester rejects a holding lawyer's completion submission; resolved by a
Cynosure admin after reviewing evidence from both sides.
"""
import uuid
from django.db import models
from apps.common.models import TimeStampedModel


class Dispute(TimeStampedModel):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved_release', 'Resolved — Released to Lawyer'),
        ('resolved_refund', 'Resolved — Refunded to Requester'),
        ('resolved_split', 'Resolved — Split'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    engagement = models.OneToOneField(
        'brief_connect.BriefEngagement',
        on_delete=models.CASCADE,
        related_name='dispute',
    )
    raised_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='disputes_raised',
    )
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='disputes_resolved',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    split_lawyer_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    split_requester_refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Dispute on engagement {self.engagement_id} ({self.status})"


class DisputeEvidence(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='evidence')
    submitted_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='dispute_evidence',
    )
    note = models.TextField(blank=True)
    attachment = models.FileField(upload_to='disputes/evidence/', blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Evidence by {self.submitted_by.full_name} on dispute {self.dispute_id}"
