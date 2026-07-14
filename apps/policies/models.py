"""
Versioned consent policies shown at key checkpoints (posting a brief, applying,
funding escrow, confirming/rejecting completion) before the user may proceed.
"""
from django.db import models
from apps.common.models import TimeStampedModel


class PolicyDocument(TimeStampedModel):
    """
    A versioned policy document for a specific checkpoint. Only one version
    per checkpoint should be `is_active` at a time — that is the version
    users are required to accept.
    """
    CHECKPOINT_CHOICES = [
        ('posting', 'Posting a Brief Request'),
        ('applying', 'Applying to a Brief Request'),
        ('escrow', 'Funding Escrow'),
        ('completion', 'Confirming or Rejecting Completion'),
    ]

    checkpoint = models.CharField(max_length=20, choices=CHECKPOINT_CHOICES, db_index=True)
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-version']
        unique_together = ['checkpoint', 'version']
        indexes = [
            models.Index(fields=['checkpoint', 'is_active']),
        ]

    def __str__(self):
        return f"{self.get_checkpoint_display()} v{self.version}"

    @classmethod
    def current(cls, checkpoint):
        return cls.objects.filter(checkpoint=checkpoint, is_active=True).order_by('-version').first()


class PolicyAcceptance(TimeStampedModel):
    """Records that a user accepted a specific version of a policy document."""
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='policy_acceptances',
    )
    policy = models.ForeignKey(
        PolicyDocument,
        on_delete=models.CASCADE,
        related_name='acceptances',
    )

    class Meta:
        unique_together = ['user', 'policy']

    def __str__(self):
        return f"{self.user.full_name} accepted {self.policy}"
