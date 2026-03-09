"""
Serializers for judges endpoints.
"""
from rest_framework import serializers
from .models import Judge, JudgeAvailability, JudgeTransfer, JudgeLeave


class JudgeListSerializer(serializers.ModelSerializer):
    """Minimal serializer for judge listings."""
    title_display = serializers.CharField(source='get_title_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    full_name = serializers.ReadOnlyField()
    formal_name = serializers.ReadOnlyField()
    court_name = serializers.CharField(source='court.name', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    
    class Meta:
        model = Judge
        fields = [
            'id', 'title', 'title_display', 'first_name', 'last_name',
            'full_name', 'formal_name', 'photo',
            'court', 'court_name', 'division', 'division_name',
            'status', 'status_display', 'is_active',
            'total_cases', 'pending_cases', 'follower_count',
        ]


class JudgeDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for judge information."""
    title_display = serializers.CharField(source='get_title_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    full_name = serializers.ReadOnlyField()
    formal_name = serializers.ReadOnlyField()
    court_name = serializers.CharField(source='court.name', read_only=True)
    court_type = serializers.CharField(source='court.court_type', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    courtroom_name = serializers.CharField(source='default_courtroom.name', read_only=True)
    upcoming_availability = serializers.SerializerMethodField()
    
    class Meta:
        model = Judge
        fields = [
            'id', 'title', 'title_display',
            'first_name', 'last_name', 'other_names',
            'full_name', 'formal_name', 'photo',
            'court', 'court_name', 'court_type',
            'division', 'division_name',
            'status', 'status_display', 'status_note',
            'status_effective_from', 'status_effective_until',
            'email', 'phone_number', 'office_location',
            'biography', 'appointment_date', 'year_of_call',
            'qualifications', 'areas_of_expertise', 'previous_positions',
            'default_courtroom', 'courtroom_name',
            'sitting_days', 'sitting_time_start', 'sitting_time_end',
            'total_cases', 'pending_cases', 'follower_count',
            'is_chief_judge', 'is_active',
            'upcoming_availability',
            'created_at', 'updated_at',
        ]
    
    def get_upcoming_availability(self, obj):
        """Get next 7 days availability."""
        from datetime import date, timedelta
        today = date.today()
        end_date = today + timedelta(days=7)
        
        availability = obj.availability_records.filter(
            date__gte=today,
            date__lte=end_date
        ).order_by('date')
        
        return JudgeAvailabilitySerializer(availability, many=True).data


class JudgeCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating judges."""
    
    class Meta:
        model = Judge
        fields = [
            'title', 'first_name', 'last_name', 'other_names',
            'court', 'division',
            'status', 'status_note', 'status_effective_from', 'status_effective_until',
            'email', 'phone_number', 'office_location',
            'photo', 'biography', 'appointment_date', 'year_of_call',
            'qualifications', 'areas_of_expertise', 'previous_positions',
            'default_courtroom',
            'sitting_days', 'sitting_time_start', 'sitting_time_end',
            'is_chief_judge', 'is_active',
        ]


class JudgeAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for judge availability."""
    availability_display = serializers.CharField(source='get_availability_display', read_only=True)
    judge_name = serializers.CharField(source='judge.full_name', read_only=True)
    alternate_judge_name = serializers.CharField(source='alternate_judge.full_name', read_only=True)
    
    class Meta:
        model = JudgeAvailability
        fields = [
            'id', 'judge', 'judge_name', 'date',
            'availability', 'availability_display', 'reason',
            'start_time', 'end_time',
            'alternate_judge', 'alternate_judge_name',
            'alternate_courtroom',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class JudgeAvailabilityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating judge availability records."""
    
    class Meta:
        model = JudgeAvailability
        fields = [
            'judge', 'date', 'availability', 'reason',
            'start_time', 'end_time',
            'alternate_judge', 'alternate_courtroom',
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class JudgeTransferSerializer(serializers.ModelSerializer):
    """Serializer for judge transfers."""
    judge_name = serializers.CharField(source='judge.full_name', read_only=True)
    from_court_name = serializers.CharField(source='from_court.name', read_only=True)
    to_court_name = serializers.CharField(source='to_court.name', read_only=True)
    
    class Meta:
        model = JudgeTransfer
        fields = [
            'id', 'judge', 'judge_name',
            'from_court', 'from_court_name', 'from_division',
            'to_court', 'to_court_name', 'to_division',
            'effective_date', 'reason', 'transfer_order_reference',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class JudgeLeaveSerializer(serializers.ModelSerializer):
    """Serializer for judge leave records."""
    judge_name = serializers.CharField(source='judge.full_name', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    acting_judge_name = serializers.CharField(source='acting_judge.full_name', read_only=True)
    
    class Meta:
        model = JudgeLeave
        fields = [
            'id', 'judge', 'judge_name',
            'leave_type', 'leave_type_display',
            'start_date', 'end_date', 'reason',
            'is_approved', 'approved_at',
            'acting_judge', 'acting_judge_name',
            'created_at',
        ]
        read_only_fields = ['id', 'is_approved', 'approved_at', 'created_at']


class JudgeStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating judge status."""
    status = serializers.ChoiceField(choices=Judge.STATUS_CHOICES)
    status_note = serializers.CharField(required=False, allow_blank=True)
    status_effective_from = serializers.DateField(required=False)
    status_effective_until = serializers.DateField(required=False)


class JudgeStatisticsSerializer(serializers.Serializer):
    """Serializer for judge statistics."""
    total_judges = serializers.IntegerField()
    active_judges = serializers.IntegerField()
    judges_on_leave = serializers.IntegerField()
    judges_by_court = serializers.DictField()
    judges_by_status = serializers.DictField()
