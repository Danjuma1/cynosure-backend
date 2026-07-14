from django.contrib import admin
from .models import Dispute, DisputeEvidence


class DisputeEvidenceInline(admin.TabularInline):
    model = DisputeEvidence
    extra = 0
    readonly_fields = ['submitted_by', 'note', 'attachment', 'created_at']


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['id', 'engagement', 'raised_by', 'status', 'resolved_by', 'created_at']
    list_filter = ['status']
    search_fields = ['engagement__requester__email', 'engagement__holding_lawyer__email']
    raw_id_fields = ['engagement', 'raised_by', 'resolved_by']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [DisputeEvidenceInline]
