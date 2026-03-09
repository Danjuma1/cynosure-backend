"""E-Filing app configuration."""
from django.apps import AppConfig


class EfilingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.efiling'
    verbose_name = 'E-Filing'
