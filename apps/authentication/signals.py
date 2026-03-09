"""
Signal handlers for authentication app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """Handle new user creation."""
    if created:
        # Additional setup for new users could go here
        pass
