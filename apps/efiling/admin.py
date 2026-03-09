from django.contrib import admin
from .models import Filing, FilingDocument, FilingComment

@admin.register(Filing)
class FilingAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'title', 'filed_by', 'court', 'status', 'submitted_at']
    list_filter = ['status', 'filing_type', 'court']
    search_fields = ['reference_number', 'title', 'filed_by__email']

@admin.register(FilingDocument)
class FilingDocumentAdmin(admin.ModelAdmin):
    list_display = ['filing', 'title', 'document_type', 'order']
    list_filter = ['document_type']
    search_fields = ['title', 'filing__reference_number']

@admin.register(FilingComment)
class FilingCommentAdmin(admin.ModelAdmin):
    list_display = ['filing', 'user', 'is_internal', 'created_at']
    list_filter = ['is_internal']
    search_fields = ['filing__reference_number', 'user__email']