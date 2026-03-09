from django.contrib import admin
from .models import CauseList, CauseListEntry, CauseListChange, CauseListSubscription, CauseListTemplate

@admin.register(CauseList)
class CauseListAdmin(admin.ModelAdmin):
    list_display = ['court', 'judge', 'date', 'status', 'total_cases']
    list_filter = ['status', 'date', 'court']
    search_fields = ['court__name', 'judge__last_name']

@admin.register(CauseListEntry)
class CauseListEntryAdmin(admin.ModelAdmin):
    list_display = ['cause_list', 'case_number', 'parties', 'status', 'order_number']
    list_filter = ['status', 'case_type']
    search_fields = ['case_number', 'parties']

@admin.register(CauseListChange)
class CauseListChangeAdmin(admin.ModelAdmin):
    list_display = ['cause_list', 'change_type', 'changed_by', 'created_at']
    list_filter = ['change_type', 'created_at']
    search_fields = ['cause_list__court__name']

@admin.register(CauseListSubscription)
class CauseListSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'court', 'judge', 'is_active']
    list_filter = ['is_active', 'notify_new_list', 'notify_changes']
    search_fields = ['user__email']

@admin.register(CauseListTemplate)
class CauseListTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'court', 'file_type', 'is_active']
    list_filter = ['file_type', 'is_active']
    search_fields = ['name', 'court__name']