"""
Judges app configuration.
"""
from django.apps import AppConfig


class JudgesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.judges'
    verbose_name = 'Judges'
