"""
Settings package initialization.
Import settings based on DJANGO_SETTINGS_MODULE environment variable.
"""
import os

environment = os.environ.get('DJANGO_ENV', 'development')

if environment == 'production':
    from .production import *
elif environment == 'staging':
    from .production import *
else:
    from .development import *
