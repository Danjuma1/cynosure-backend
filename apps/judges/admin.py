from django.contrib import admin
from .models import Judge, JudgeAvailability, JudgeTransfer, JudgeLeave, JudgeRating

@admin.register(Judge)
class JudgeAdmin(admin.ModelAdmin):
    list_display = ['formal_name', 'court', 'division', 'status', 'is_active']
    list_filter = ['status', 'court', 'is_active']
    search_fields = ['first_name', 'last_name', 'email']

@admin.register(JudgeAvailability)
class JudgeAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['judge', 'date', 'availability', 'reason']
    list_filter = ['availability', 'date']
    search_fields = ['judge__last_name']

@admin.register(JudgeTransfer)
class JudgeTransferAdmin(admin.ModelAdmin):
    list_display = ['judge', 'from_court', 'to_court', 'effective_date']
    list_filter = ['effective_date']
    search_fields = ['judge__last_name']

@admin.register(JudgeLeave)
class JudgeLeaveAdmin(admin.ModelAdmin):
    list_display = ['judge', 'leave_type', 'start_date', 'end_date', 'is_approved']
    list_filter = ['leave_type', 'is_approved']
    search_fields = ['judge__last_name']

@admin.register(JudgeRating)
class JudgeRatingAdmin(admin.ModelAdmin):
    list_display = ['judge', 'criteria', 'rating', 'is_verified', 'is_published']
    list_filter = ['criteria', 'rating', 'is_verified', 'is_published']
    search_fields = ['judge__last_name']