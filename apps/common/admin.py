from django.contrib import admin
from .models import AuditLog, SystemConfiguration

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_id', 'created_at']
    list_filter = ['action', 'model_name', 'created_at']
    search_fields = ['user__email', 'model_name', 'object_id']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'changes', 'ip_address', 'created_at']

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ['key', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['key', 'description']