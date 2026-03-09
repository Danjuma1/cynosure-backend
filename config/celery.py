"""
Celery configuration for Cynosure project.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('cynosure')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    # Daily cause list scraping - runs at 5 AM Lagos time
    'scrape-cause-lists-daily': {
        'task': 'apps.scraping.tasks.scrape_all_courts',
        'schedule': crontab(hour=5, minute=0),
        'options': {'queue': 'scraping'},
    },
    
    # Retry failed scraping tasks - every 2 hours
    'retry-failed-scraping': {
        'task': 'apps.scraping.tasks.retry_failed_scrapes',
        'schedule': crontab(minute=0, hour='*/2'),
        'options': {'queue': 'scraping'},
    },
    
    # Generate daily summaries - at 7 AM
    'generate-daily-summaries': {
        'task': 'apps.notifications.tasks.generate_daily_summaries',
        'schedule': crontab(hour=7, minute=0),
        'options': {'queue': 'notifications'},
    },
    
    # Clean up temporary files - daily at midnight
    'cleanup-temp-files': {
        'task': 'apps.scraping.tasks.cleanup_temp_files',
        'schedule': crontab(hour=0, minute=0),
        'options': {'queue': 'default'},
    },
    
    # Process pending notifications - every 5 minutes
    'process-pending-notifications': {
        'task': 'apps.notifications.tasks.process_pending_notifications',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'notifications'},
    },
    
    # Update cache for frequently accessed data - every 15 minutes
    'refresh-court-cache': {
        'task': 'apps.courts.tasks.refresh_court_cache',
        'schedule': crontab(minute='*/15'),
        'options': {'queue': 'default'},
    },
    
    # Send reminder notifications - at 6 AM for today's cases
    'send-case-reminders': {
        'task': 'apps.notifications.tasks.send_case_reminders',
        'schedule': crontab(hour=6, minute=0),
        'options': {'queue': 'notifications'},
    },
    
    # Archive old notifications - weekly on Sunday at midnight
    'archive-old-notifications': {
        'task': 'apps.notifications.tasks.archive_old_notifications',
        'schedule': crontab(hour=0, minute=0, day_of_week=0),
        'options': {'queue': 'default'},
    },
    
    # Generate analytics report - weekly on Monday at 8 AM
    'generate-weekly-analytics': {
        'task': 'apps.adminpanel.tasks.generate_weekly_analytics',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),
        'options': {'queue': 'default'},
    },
}

# Task routing
app.conf.task_routes = {
    'apps.scraping.tasks.*': {'queue': 'scraping'},
    'apps.notifications.tasks.*': {'queue': 'notifications'},
    'apps.search.tasks.*': {'queue': 'search'},
    '*': {'queue': 'default'},
}

# Task priority
app.conf.task_default_priority = 5

# Result expiration
app.conf.result_expires = 3600  # 1 hour


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f'Request: {self.request!r}')
