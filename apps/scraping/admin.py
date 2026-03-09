from django.contrib import admin
from .models import ScraperConfig, ScraperRun, ParsedDocument

@admin.register(ScraperConfig)
class ScraperConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'court', 'scraper_type', 'is_active', 'last_run']
    list_filter = ['scraper_type', 'is_active', 'court']
    search_fields = ['name', 'court__name']

@admin.register(ScraperRun)
class ScraperRunAdmin(admin.ModelAdmin):
    list_display = ['config', 'status', 'items_found', 'items_created', 'started_at']
    list_filter = ['status', 'started_at']
    search_fields = ['config__name']

@admin.register(ParsedDocument)
class ParsedDocumentAdmin(admin.ModelAdmin):
    list_display = ['court', 'date', 'status', 'reviewed_by', 'created_at']
    list_filter = ['status', 'court']
    search_fields = ['court__name']