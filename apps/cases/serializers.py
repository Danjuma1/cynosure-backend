"""
Serializers for cases endpoints.
"""
from rest_framework import serializers
from .models import Case, CaseHearing, CaseDocument, CaseNote, CaseTimeline


class CaseListSerializer(serializers.ModelSerializer):
    """Minimal serializer for case listings."""
    case_type_display = serializers.CharField(source='get_case_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    judge_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Case
        fields = [
            'id', 'case_number', 'parties', 'applicant', 'respondent',
            'case_type', 'case_type_display',
            'status', 'status_display',
            'court', 'court_name', 'judge', 'judge_name',
            'next_hearing_date', 'total_hearings', 'follower_count',
        ]
    
    def get_judge_name(self, obj):
        if obj.judge:
            return obj.judge.formal_name
        return None


class CaseHearingSerializer(serializers.ModelSerializer):
    """Serializer for case hearings."""
    outcome_display = serializers.CharField(source='get_outcome_display', read_only=True)
    judge_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CaseHearing
        fields = [
            'id', 'date', 'time', 'judge', 'judge_name', 'courtroom',
            'outcome', 'outcome_display', 'outcome_notes',
            'next_date', 'adjournment_reason',
            'applicant_present', 'respondent_present',
            'counsel_applicant_present', 'counsel_respondent_present',
            'proceedings', 'orders',
            'created_at',
        ]
    
    def get_judge_name(self, obj):
        if obj.judge:
            return obj.judge.formal_name
        return None


class CaseDocumentSerializer(serializers.ModelSerializer):
    """Serializer for case documents."""
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = CaseDocument
        fields = [
            'id', 'title', 'document_type', 'document_type_display',
            'description', 'file', 'file_size', 'file_type',
            'filing_date', 'filed_by', 'is_public',
            'created_at',
        ]


class CaseTimelineSerializer(serializers.ModelSerializer):
    """Serializer for case timeline."""
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = CaseTimeline
        fields = [
            'id', 'event_type', 'event_type_display',
            'event_date', 'title', 'description', 'metadata',
        ]


class CaseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for case information."""
    case_type_display = serializers.CharField(source='get_case_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    court_type = serializers.CharField(source='court.court_type', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    judge_name = serializers.SerializerMethodField()
    recent_hearings = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    
    class Meta:
        model = Case
        fields = [
            'id', 'case_number', 'suit_number', 'old_case_numbers',
            'court', 'court_name', 'court_type',
            'division', 'division_name',
            'judge', 'judge_name',
            'parties', 'applicant', 'respondent',
            'co_applicants', 'co_respondents', 'interested_parties',
            'case_type', 'case_type_display',
            'matter_type', 'subject_matter',
            'status', 'status_display', 'status_note',
            'filing_date', 'first_hearing_date', 'last_hearing_date',
            'next_hearing_date', 'judgment_date',
            'judgment_summary', 'ruling',
            'counsel_for_applicant', 'counsel_for_respondent',
            'total_adjournments', 'total_hearings', 'follower_count',
            'recent_hearings', 'timeline',
            'created_at', 'updated_at',
        ]
    
    def get_judge_name(self, obj):
        if obj.judge:
            return obj.judge.formal_name
        return None
    
    def get_recent_hearings(self, obj):
        hearings = obj.hearings.all()[:10]
        return CaseHearingSerializer(hearings, many=True).data
    
    def get_timeline(self, obj):
        timeline = obj.timeline.all()[:20]
        return CaseTimelineSerializer(timeline, many=True).data


class CaseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating cases."""
    
    class Meta:
        model = Case
        fields = [
            'case_number', 'suit_number',
            'court', 'division', 'judge',
            'parties', 'applicant', 'respondent',
            'co_applicants', 'co_respondents', 'interested_parties',
            'case_type', 'matter_type', 'subject_matter',
            'status', 'filing_date',
            'counsel_for_applicant', 'counsel_for_respondent',
        ]


class CaseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating cases."""
    
    class Meta:
        model = Case
        fields = [
            'division', 'judge',
            'parties', 'applicant', 'respondent',
            'co_applicants', 'co_respondents', 'interested_parties',
            'matter_type', 'subject_matter',
            'status', 'status_note',
            'next_hearing_date',
            'counsel_for_applicant', 'counsel_for_respondent',
        ]


class CaseNoteSerializer(serializers.ModelSerializer):
    """Serializer for case notes."""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = CaseNote
        fields = [
            'id', 'case', 'user', 'user_name',
            'title', 'content', 'is_private',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class CaseSearchSerializer(serializers.Serializer):
    """Serializer for case search parameters."""
    q = serializers.CharField(required=False, help_text="Search query")
    case_number = serializers.CharField(required=False)
    parties = serializers.CharField(required=False)
    court = serializers.UUIDField(required=False)
    judge = serializers.UUIDField(required=False)
    case_type = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class CaseSuggestionSerializer(serializers.Serializer):
    """Serializer for case suggestions (fuzzy search)."""
    id = serializers.UUIDField()
    case_number = serializers.CharField()
    parties = serializers.CharField()
    score = serializers.FloatField()
