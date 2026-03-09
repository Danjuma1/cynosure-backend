"""
Serializers for courts endpoints.
"""
from rest_framework import serializers
from .models import Court, Division, Courtroom, Panel, CourtRule, CourtHoliday, CourtContact


class CourtListSerializer(serializers.ModelSerializer):
    """Minimal serializer for court listings."""
    court_type_display = serializers.CharField(source='get_court_type_display', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    
    class Meta:
        model = Court
        fields = [
            'id', 'name', 'code', 'court_type', 'court_type_display',
            'state', 'state_display', 'city', 'is_active',
            'total_judges', 'total_divisions', 'follower_count',
        ]


class CourtDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for court information."""
    court_type_display = serializers.CharField(source='get_court_type_display', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    full_address = serializers.ReadOnlyField()
    divisions = serializers.SerializerMethodField()
    rules = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()
    
    class Meta:
        model = Court
        fields = [
            'id', 'name', 'code', 'court_type', 'court_type_display',
            'state', 'state_display', 'address', 'city', 'postal_code',
            'full_address', 'latitude', 'longitude',
            'phone_number', 'email', 'website',
            'jurisdiction', 'jurisdiction_areas', 'description',
            'established_date', 'chief_judge_id',
            'is_active', 'working_days', 'working_hours',
            'total_judges', 'total_divisions', 'follower_count',
            'divisions', 'rules', 'contacts',
            'created_at', 'updated_at',
        ]
    
    def get_divisions(self, obj):
        divisions = obj.divisions.filter(is_active=True)[:10]
        return DivisionListSerializer(divisions, many=True).data
    
    def get_rules(self, obj):
        rules = obj.rules.filter(is_current=True)[:5]
        return CourtRuleSerializer(rules, many=True).data
    
    def get_contacts(self, obj):
        contacts = obj.contacts.filter(is_active=True)
        return CourtContactSerializer(contacts, many=True).data


class CourtCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating courts (admin only)."""
    
    class Meta:
        model = Court
        fields = [
            'name', 'code', 'court_type', 'state',
            'address', 'city', 'postal_code', 'latitude', 'longitude',
            'phone_number', 'email', 'website',
            'jurisdiction', 'jurisdiction_areas', 'description',
            'established_date', 'chief_judge_id',
            'is_active', 'working_days', 'working_hours',
        ]
    
    def validate_code(self, value):
        """Ensure code is unique."""
        instance = self.instance
        if Court.objects.filter(code=value).exclude(pk=instance.pk if instance else None).exists():
            raise serializers.ValidationError("A court with this code already exists.")
        return value.upper()


class DivisionListSerializer(serializers.ModelSerializer):
    """Minimal serializer for division listings."""
    court_name = serializers.CharField(source='court.name', read_only=True)
    
    class Meta:
        model = Division
        fields = [
            'id', 'name', 'code', 'court', 'court_name',
            'is_active', 'total_judges',
        ]


class DivisionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for division information."""
    court_name = serializers.CharField(source='court.name', read_only=True)
    courtrooms = serializers.SerializerMethodField()
    
    class Meta:
        model = Division
        fields = [
            'id', 'name', 'code', 'court', 'court_name',
            'description', 'building', 'floor',
            'phone_number', 'email',
            'is_active', 'head_judge_id', 'total_judges',
            'courtrooms',
            'created_at', 'updated_at',
        ]
    
    def get_courtrooms(self, obj):
        courtrooms = obj.courtrooms.filter(is_active=True)
        return CourtroomSerializer(courtrooms, many=True).data


class DivisionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating divisions."""
    
    class Meta:
        model = Division
        fields = [
            'court', 'name', 'code', 'description',
            'building', 'floor', 'phone_number', 'email',
            'is_active', 'head_judge_id',
        ]


class CourtroomSerializer(serializers.ModelSerializer):
    """Serializer for courtrooms."""
    court_name = serializers.CharField(source='court.name', read_only=True)
    division_name = serializers.CharField(source='division.name', read_only=True)
    
    class Meta:
        model = Courtroom
        fields = [
            'id', 'name', 'number', 'court', 'court_name',
            'division', 'division_name',
            'building', 'floor', 'capacity',
            'has_video_conferencing', 'has_recording', 'is_accessible',
            'is_active',
        ]


class PanelListSerializer(serializers.ModelSerializer):
    """Minimal serializer for panel listings."""
    court_name = serializers.CharField(source='court.name', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Panel
        fields = [
            'id', 'name', 'code', 'court', 'court_name',
            'presiding_judge_id', 'member_count',
            'is_active', 'effective_from', 'effective_until',
        ]
    
    def get_member_count(self, obj):
        return len(obj.member_ids) if obj.member_ids else 0


class PanelDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for panel information."""
    court_name = serializers.CharField(source='court.name', read_only=True)
    members = serializers.SerializerMethodField()
    
    class Meta:
        model = Panel
        fields = [
            'id', 'name', 'code', 'court', 'court_name',
            'presiding_judge_id', 'member_ids', 'members',
            'is_active', 'effective_from', 'effective_until',
            'assigned_categories',
            'created_at', 'updated_at',
        ]
    
    def get_members(self, obj):
        """Get member details from judges app."""
        # This would fetch judge details - placeholder for now
        return []


class PanelCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating panels."""
    
    class Meta:
        model = Panel
        fields = [
            'court', 'name', 'code',
            'presiding_judge_id', 'member_ids',
            'is_active', 'effective_from', 'effective_until',
            'assigned_categories',
        ]


class CourtRuleSerializer(serializers.ModelSerializer):
    """Serializer for court rules."""
    court_name = serializers.CharField(source='court.name', read_only=True)
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    
    class Meta:
        model = CourtRule
        fields = [
            'id', 'court', 'court_name',
            'title', 'description', 'rule_type', 'rule_type_display',
            'document', 'file_size',
            'effective_date', 'expiry_date',
            'is_current',
            'created_at', 'updated_at',
        ]


class CourtHolidaySerializer(serializers.ModelSerializer):
    """Serializer for court holidays."""
    court_name = serializers.CharField(source='court.name', read_only=True)
    holiday_type_display = serializers.CharField(source='get_holiday_type_display', read_only=True)
    
    class Meta:
        model = CourtHoliday
        fields = [
            'id', 'court', 'court_name',
            'name', 'description',
            'start_date', 'end_date',
            'holiday_type', 'holiday_type_display',
            'is_recurring',
        ]


class CourtContactSerializer(serializers.ModelSerializer):
    """Serializer for court contacts."""
    contact_type_display = serializers.CharField(source='get_contact_type_display', read_only=True)
    
    class Meta:
        model = CourtContact
        fields = [
            'id', 'contact_type', 'contact_type_display',
            'name', 'title', 'phone_number', 'email',
            'office_location', 'is_active',
        ]


class CourtStatisticsSerializer(serializers.Serializer):
    """Serializer for court statistics."""
    total_courts = serializers.IntegerField()
    courts_by_type = serializers.DictField()
    courts_by_state = serializers.DictField()
    active_courts = serializers.IntegerField()
    total_judges = serializers.IntegerField()
    total_divisions = serializers.IntegerField()
