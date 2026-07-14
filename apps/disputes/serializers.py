from rest_framework import serializers
from .models import Dispute, DisputeEvidence


class DisputeEvidenceSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.CharField(source='submitted_by.full_name', read_only=True)

    class Meta:
        model = DisputeEvidence
        fields = ['id', 'dispute', 'submitted_by', 'submitted_by_name', 'note', 'attachment', 'created_at']
        read_only_fields = ['id', 'dispute', 'submitted_by', 'created_at']


class DisputeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    raised_by_name = serializers.CharField(source='raised_by.full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)
    evidence = DisputeEvidenceSerializer(many=True, read_only=True)
    requester_name = serializers.CharField(source='engagement.requester.full_name', read_only=True)
    holding_lawyer_name = serializers.CharField(source='engagement.holding_lawyer.full_name', read_only=True)
    agreed_fee = serializers.DecimalField(source='engagement.agreed_fee', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Dispute
        fields = [
            'id', 'engagement', 'raised_by', 'raised_by_name', 'reason', 'status', 'status_display',
            'resolution_notes', 'resolved_by', 'resolved_by_name', 'resolved_at',
            'split_lawyer_amount', 'split_requester_refund_amount',
            'requester_name', 'holding_lawyer_name', 'agreed_fee',
            'evidence', 'created_at',
        ]
        read_only_fields = [
            'id', 'engagement', 'raised_by', 'status', 'resolution_notes',
            'resolved_by', 'resolved_at', 'split_lawyer_amount', 'split_requester_refund_amount', 'created_at',
        ]
