"""
Scraping app - Models, Tasks, and Views for cause list scraping.
"""
import uuid
from django.db import models
from apps.common.models import BaseModel, TimeStampedModel


# ============== MODELS ==============

class ScraperConfig(BaseModel):
    """Configuration for court scrapers."""
    court = models.ForeignKey('courts.Court', on_delete=models.CASCADE, related_name='scraper_configs')
    
    name = models.CharField(max_length=255)
    scraper_type = models.CharField(max_length=50, choices=[
        ('pdf', 'PDF Scraper'),
        ('html', 'HTML Scraper'),
        ('api', 'API Scraper'),
    ])
    
    # Configuration
    source_url = models.URLField(blank=True)
    config = models.JSONField(default=dict)
    
    # Schedule
    is_active = models.BooleanField(default=True)
    schedule_cron = models.CharField(max_length=100, default='0 5 * * *')
    
    # Statistics
    last_run = models.DateTimeField(null=True, blank=True)
    last_success = models.DateTimeField(null=True, blank=True)
    total_runs = models.PositiveIntegerField(default=0)
    successful_runs = models.PositiveIntegerField(default=0)
    failed_runs = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['court__name']
    
    def __str__(self):
        return f"{self.name} - {self.court.name}"


class ScraperRun(TimeStampedModel):
    """Record of scraper execution."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(ScraperConfig, on_delete=models.CASCADE, related_name='runs')
    
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    items_found = models.PositiveIntegerField(default=0)
    items_created = models.PositiveIntegerField(default=0)
    items_updated = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list)
    
    # Logs
    log = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.config.name} - {self.created_at}"


class ParsedDocument(TimeStampedModel):
    """Temporarily stored parsed document data."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    source_file = models.FileField(upload_to='parsed_documents/')
    file_hash = models.CharField(max_length=64, db_index=True)
    
    court = models.ForeignKey('courts.Court', on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    
    parsed_data = models.JSONField(default=dict)
    parsing_errors = models.JSONField(default=list)
    
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('parsed', 'Parsed'),
        ('reviewed', 'Reviewed'),
        ('imported', 'Imported'),
        ('rejected', 'Rejected'),
    ], default='pending')
    
    reviewed_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
