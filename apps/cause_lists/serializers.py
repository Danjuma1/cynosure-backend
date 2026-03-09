"""
Serializers for cause lists endpoints.
"""
from rest_framework import serializers
from .models import CauseList, CauseListEntry, CauseListChange, CauseListSubscription


class CauseListEntrySerializer(serializers.ModelSerializer):
    """Serializer for cause list entries."""
    case_type_display = serializers.CharField(source='get_case_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CauseListEntry
        fields = [
            'id', 'case', 'case_number', 'suit_number',
            'parties', 'applicant', 'respondent',
            'matter_type', 'case_type', 'case_type_display',
            'order_number', 'scheduled_time', 'courtroom',
            'status', 'status_display',
            'outcome', 'next_date', 'adjournment_reason',
            'counsel_for_applicant', 'counsel_for_respondent',
            'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CauseListEntryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating cause list entries."""
    
    class Meta:
        model = CauseListEntry
        fields = [
            'cause_list', 'case', 'case_number', 'suit_number',
            'parties', 'applicant', 'respondent',
            'matter_type', 'case_type',
            'order_number', 'scheduled_time', 'courtroom',
            'status', 'notes',
            'counsel_for_applicant', 'counsel_for_respondent',
        ]


class CauseListSerializer(serializers.ModelSerializer):
    """Serializer for cause lists."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    court_type = serializers.CharField(source='court.court_type', read_only=True)
    judge_name = serializers.SerializerMethodField()
    panel_name = serializers.CharField(source='panel.name', read_only=True)
    courtroom_name = serializers.CharField(source='courtroom.name', read_only=True)
    entries = CauseListEntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = CauseList
        fields = [
            'id', 'court', 'court_name', 'court_type',
            'judge', 'judge_name', 'panel', 'panel_name',
            'date', 'status', 'status_display',
            'courtroom', 'courtroom_name',
            'start_time', 'end_time',
            'status_note', 'adjournment_reason', 'not_sitting_reason',
            'pdf_file', 'source',
            'published_at', 'total_cases', 'version',
            'entries',
            'created_at', 'updated_at',
        ]
    
    def get_judge_name(self, obj):
        if obj.judge:
            return obj.judge.formal_name
        return None


class CauseListListSerializer(serializers.ModelSerializer):
    """Minimal serializer for cause list listings."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    judge_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CauseList
        fields = [
            'id', 'court', 'court_name',
            'judge', 'judge_name', 'panel',
            'date', 'status', 'status_display',
            'start_time', 'total_cases',
            'published_at',
        ]
    
    def get_judge_name(self, obj):
        if obj.judge:
            return obj.judge.formal_name
        return None


class CauseListCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating cause lists."""
    entries = CauseListEntryCreateSerializer(many=True, required=False)
    
    class Meta:
        model = CauseList
        fields = [
            'court', 'judge', 'panel', 'date',
            'courtroom', 'start_time', 'end_time',
            'status', 'status_note',
            'pdf_file', 'source', 'source_url',
            'entries',
        ]
    
    def validate(self, attrs):
        # Either judge or panel must be specified
        if not attrs.get('judge') and not attrs.get('panel'):
            raise serializers.ValidationError(
                "Either judge or panel must be specified."
            )
        return attrs
    
    def create(self, validated_data):
        entries_data = validated_data.pop('entries', [])
        cause_list = CauseList.objects.create(**validated_data)
        
        for idx, entry_data in enumerate(entries_data):
            entry_data['cause_list'] = cause_list
            if 'order_number' not in entry_data:
                entry_data['order_number'] = idx + 1
            CauseListEntry.objects.create(**entry_data)
        
        cause_list.update_case_count()
        return cause_list


class CauseListUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating cause lists."""
    
    class Meta:
        model = CauseList
        fields = [
            'courtroom', 'start_time', 'end_time',
            'status', 'status_note',
            'adjournment_reason', 'not_sitting_reason',
        ]


class CauseListStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating cause list status."""
    status = serializers.ChoiceField(choices=CauseList.STATUS_CHOICES)
    status_note = serializers.CharField(required=False, allow_blank=True)
    adjournment_reason = serializers.CharField(required=False, allow_blank=True)
    not_sitting_reason = serializers.CharField(required=False, allow_blank=True)


class CauseListChangeSerializer(serializers.ModelSerializer):
    """Serializer for cause list changes."""
    change_type_display = serializers.CharField(source='get_change_type_display', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)
    
    class Meta:
        model = CauseListChange
        fields = [
            'id', 'cause_list', 'entry',
            'change_type', 'change_type_display',
            'field_name', 'old_value', 'new_value',
            'changes', 'changed_by', 'changed_by_name',
            'created_at',
        ]


class CauseListSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for cause list subscriptions."""
    court_name = serializers.CharField(source='court.name', read_only=True)
    judge_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CauseListSubscription
        fields = [
            'id', 'court', 'court_name',
            'judge', 'judge_name', 'case_number',
            'notify_new_list', 'notify_changes',
            'notify_status_change', 'notify_adjournment',
            'email_notifications', 'push_notifications',
            'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_judge_name(self, obj):
        if obj.judge:
            return obj.judge.formal_name
        return None


class CauseListUploadSerializer(serializers.Serializer):
    """Serializer for uploading cause list PDFs."""
    court = serializers.UUIDField()
    judge = serializers.UUIDField(required=False)
    panel = serializers.UUIDField(required=False)
    date = serializers.DateField()
    pdf_file = serializers.FileField()
    
    def validate(self, attrs):
        if not attrs.get('judge') and not attrs.get('panel'):
            raise serializers.ValidationError(
                "Either judge or panel must be specified."
            )
        return attrs


class DailyCauseListSerializer(serializers.Serializer):
    """Serializer for daily cause list summary."""
    date = serializers.DateField()
    total_lists = serializers.IntegerField()
    by_status = serializers.DictField()
    courts = serializers.ListField()
