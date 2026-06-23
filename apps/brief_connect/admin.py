from django.contrib import admin
from .models import BriefRequest, BriefApplication, BriefEngagement, BriefReview


@admin.register(BriefRequest)
class BriefRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'requester', 'court', 'hearing_date', 'brief_type', 'status', 'application_count', 'created_at']
    list_filter = ['status', 'brief_type', 'hearing_date']
    search_fields = ['case_number', 'parties', 'requester__email', 'court__name']
    raw_id_fields = ['requester', 'court', 'judge', 'cause_list_entry', 'case']
    readonly_fields = ['application_count', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(BriefApplication)
class BriefApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'applicant', 'brief_request', 'status', 'proposed_fee', 'created_at']
    list_filter = ['status']
    search_fields = ['applicant__email', 'brief_request__case_number']
    raw_id_fields = ['applicant', 'brief_request']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BriefEngagement)
class BriefEngagementAdmin(admin.ModelAdmin):
    list_display = ['id', 'requester', 'holding_lawyer', 'status', 'agreed_fee', 'completed_at']
    list_filter = ['status']
    search_fields = ['requester__email', 'holding_lawyer__email']
    raw_id_fields = ['requester', 'holding_lawyer', 'brief_request']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BriefReview)
class BriefReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'reviewer', 'reviewee', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['reviewer__email', 'reviewee__email']
    raw_id_fields = ['reviewer', 'reviewee', 'engagement']
    readonly_fields = ['created_at']
