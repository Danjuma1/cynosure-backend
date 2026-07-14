"""
In-app chat for a confirmed Brief Connect engagement. Always exactly the
two engagement parties — no separate Conversation model needed.
"""
from django.db import models
from apps.common.models import TimeStampedModel


def chat_attachment_upload_to(instance, filename):
    return f'brief_connect/chat/{instance.engagement_id}/{filename}'


class Message(TimeStampedModel):
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('document', 'Document'),
        ('voice', 'Voice Note'),
    ]

    engagement = models.ForeignKey(
        'brief_connect.BriefEngagement',
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='brief_chat_messages',
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='text')
    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to=chat_attachment_upload_to, blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['engagement', 'created_at']),
        ]

    def __str__(self):
        return f"Message from {self.sender.full_name} in engagement {self.engagement_id}"
