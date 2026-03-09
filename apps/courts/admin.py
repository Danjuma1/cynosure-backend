from django.contrib import admin
from .models import Court, Division, Courtroom, Panel, CourtRule, CourtHoliday, CourtContact

@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ['name', 'court_type', 'state', 'is_active']
    list_filter = ['court_type', 'state', 'is_active']
    search_fields = ['name', 'code']

@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'court', 'code', 'is_active']
    list_filter = ['court', 'is_active']
    search_fields = ['name', 'code']

@admin.register(Courtroom)
class CourtroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'court', 'division', 'is_active']
    list_filter = ['court', 'is_active']
    search_fields = ['name', 'number']

@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    list_display = ['name', 'court', 'code', 'is_active']
    list_filter = ['court', 'is_active']
    search_fields = ['name', 'code']

@admin.register(CourtRule)
class CourtRuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'court', 'rule_type', 'effective_date', 'is_current']
    list_filter = ['rule_type', 'is_current', 'court']
    search_fields = ['title']

@admin.register(CourtHoliday)
class CourtHolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'court', 'start_date', 'end_date', 'holiday_type']
    list_filter = ['holiday_type', 'court']
    search_fields = ['name']

@admin.register(CourtContact)
class CourtContactAdmin(admin.ModelAdmin):
    list_display = ['court', 'contact_type', 'name', 'phone_number', 'is_active']
    list_filter = ['contact_type', 'is_active', 'court']
    search_fields = ['name', 'phone_number', 'email']