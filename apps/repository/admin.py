from django.contrib import admin
from .models import DocumentCategory, LegalDocument, DocumentBookmark

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'order']
    list_filter = ['parent']
    search_fields = ['name']

@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'category', 'court', 'is_published', 'year']
    list_filter = ['document_type', 'is_published', 'is_current', 'court']
    search_fields = ['title', 'citation']

@admin.register(DocumentBookmark)
class DocumentBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'document', 'created_at']
    search_fields = ['user__email', 'document__title']