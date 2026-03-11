"""
Django Production Settings
"""
from .base import *

DEBUG = False

# Get allowed hosts from environment
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Security settings are already enabled in base.py
# Additional production security
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Disable logging in production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
}

# Use real email backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Ensure S3 is used in production
USE_S3 = True

# Additional caching
CACHES['sessions'] = {
    'BACKEND': 'django_redis.cache.RedisCache',
    'LOCATION': os.environ.get('REDIS_URL', 'redis://redis:6379/1'),
    'OPTIONS': {
        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
    },
    'KEY_PREFIX': 'cynosure_session',
}

# Use Redis for sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 600

# Performance optimizations
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Error reporting
ADMINS = [
    ('Cynosure Admin', os.environ.get('ADMIN_EMAIL', 'admin@cynosure.ng')),
]
MANAGERS = ADMINS

# Sentry integration (if configured)
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production',
    )
