from django.contrib import admin
from .models import PolicyDocument, PolicyAcceptance


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'checkpoint', 'version', 'title', 'is_active', 'created_at']
    list_filter = ['checkpoint', 'is_active']
    search_fields = ['title', 'body']
    ordering = ['checkpoint', '-version']


@admin.register(PolicyAcceptance)
class PolicyAcceptanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'policy', 'created_at']
    list_filter = ['policy__checkpoint']
    search_fields = ['user__email']
    raw_id_fields = ['user', 'policy']
