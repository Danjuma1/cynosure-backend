from django.contrib import admin
from .models import Case, CaseHearing, CaseDocument, CaseNote, CaseTimeline, CaseTransfer

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ['case_number', 'parties', 'court', 'judge', 'status', 'next_hearing_date']
    list_filter = ['status', 'case_type', 'court']
    search_fields = ['case_number', 'parties', 'applicant', 'respondent']

@admin.register(CaseHearing)
class CaseHearingAdmin(admin.ModelAdmin):
    list_display = ['case', 'date', 'judge', 'outcome']
    list_filter = ['outcome', 'date']
    search_fields = ['case__case_number']

@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ['case', 'title', 'document_type', 'filing_date']
    list_filter = ['document_type', 'is_public']
    search_fields = ['title', 'case__case_number']

@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ['case', 'user', 'title', 'is_private']
    list_filter = ['is_private']
    search_fields = ['case__case_number', 'user__email']

@admin.register(CaseTimeline)
class CaseTimelineAdmin(admin.ModelAdmin):
    list_display = ['case', 'event_type', 'title', 'event_date']
    list_filter = ['event_type']
    search_fields = ['case__case_number', 'title']

@admin.register(CaseTransfer)
class CaseTransferAdmin(admin.ModelAdmin):
    list_display = ['case', 'from_court', 'to_court', 'transfer_date']
    list_filter = ['transfer_date']
    search_fields = ['case__case_number']