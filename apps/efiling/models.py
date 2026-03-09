"""
E-Filing app - Electronic filing system for court documents.
"""
import uuid
from django.db import models
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.common.models import BaseModel, TimeStampedModel
from apps.common.pagination import StandardResultsSetPagination
from apps.common.permissions import CanManageFilings, IsRegistryOrAdmin


# ============== MODELS ==============

class Filing(BaseModel):
    """E-filing submission."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('corrections_required', 'Corrections Required'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('filed', 'Filed'),
    ]
    
    FILING_TYPE_CHOICES = [
        ('originating', 'Originating Process'),
        ('motion', 'Motion'),
        ('affidavit', 'Affidavit'),
        ('brief', 'Brief'),
        ('reply', 'Reply'),
        ('other', 'Other'),
    ]
    
    # Reference
    reference_number = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Filer
    filed_by = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='filings')
    firm = models.ForeignKey('firms.LawFirm', on_delete=models.SET_NULL, null=True, blank=True, related_name='filings')
    
    # Court
    court = models.ForeignKey('courts.Court', on_delete=models.PROTECT, related_name='filings')
    
    # Case (if existing)
    case = models.ForeignKey('cases.Case', on_delete=models.SET_NULL, null=True, blank=True, related_name='filings')
    case_number = models.CharField(max_length=100, blank=True)
    
    # Filing details
    filing_type = models.CharField(max_length=20, choices=FILING_TYPE_CHOICES)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    
    # Parties
    applicant = models.CharField(max_length=500)
    respondent = models.CharField(max_length=500, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    status_note = models.TextField(blank=True)
    
    # Dates
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    filed_at = models.DateTimeField(null=True, blank=True)
    
    # Reviewer
    reviewed_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_filings'
    )
    
    # Filing number (assigned on approval)
    filing_number = models.CharField(max_length=100, blank=True)
    
    # Fees
    filing_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fee_paid = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['filed_by', 'status']),
            models.Index(fields=['court', 'status']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        return f"{self.reference_number} - {self.title}"


class FilingDocument(TimeStampedModel):
    """Documents attached to a filing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filing = models.ForeignKey(Filing, on_delete=models.CASCADE, related_name='documents')
    
    DOCUMENT_TYPE_CHOICES = [
        ('main', 'Main Document'),
        ('affidavit', 'Affidavit'),
        ('exhibit', 'Exhibit'),
        ('supporting', 'Supporting Document'),
    ]
    
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='filings/')
    file_size = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.filing.reference_number} - {self.title}"


class FilingComment(TimeStampedModel):
    """Comments on filings (for corrections, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filing = models.ForeignKey(Filing, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE)
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']


# ============== SERIALIZERS ==============

class FilingDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilingDocument
        fields = ['id', 'title', 'document_type', 'file', 'file_size', 'order', 'created_at']


class FilingListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    filing_type_display = serializers.CharField(source='get_filing_type_display', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    
    class Meta:
        model = Filing
        fields = [
            'id', 'reference_number', 'title', 'filing_type', 'filing_type_display',
            'court', 'court_name', 'status', 'status_display',
            'submitted_at', 'created_at',
        ]


class FilingDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    filing_type_display = serializers.CharField(source='get_filing_type_display', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    documents = FilingDocumentSerializer(many=True, read_only=True)
    filed_by_name = serializers.CharField(source='filed_by.full_name', read_only=True)
    
    class Meta:
        model = Filing
        fields = [
            'id', 'reference_number', 'title', 'description',
            'filing_type', 'filing_type_display',
            'court', 'court_name', 'case', 'case_number',
            'applicant', 'respondent',
            'status', 'status_display', 'status_note',
            'filed_by', 'filed_by_name',
            'submitted_at', 'reviewed_at', 'filed_at',
            'filing_number', 'filing_fee', 'fee_paid',
            'documents',
            'created_at', 'updated_at',
        ]


class FilingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filing
        fields = [
            'court', 'case', 'filing_type', 'title', 'description',
            'applicant', 'respondent',
        ]
    
    def create(self, validated_data):
        import uuid as uuid_lib
        validated_data['filed_by'] = self.context['request'].user
        validated_data['reference_number'] = f"FIL-{uuid_lib.uuid4().hex[:8].upper()}"
        return super().create(validated_data)


# ============== VIEWS ==============

class FilingViewSet(viewsets.ModelViewSet):
    """ViewSet for e-filings."""
    queryset = Filing.objects.filter(is_deleted=False)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['court', 'status', 'filing_type']
    permission_classes = [CanManageFilings]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FilingListSerializer
        if self.action == 'create':
            return FilingCreateSerializer
        return FilingDetailSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['registry_staff', 'super_admin']:
            return Filing.objects.filter(is_deleted=False)
        return Filing.objects.filter(filed_by=user, is_deleted=False)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit filing for review."""
        from django.utils import timezone
        filing = self.get_object()
        
        if filing.status != 'draft':
            return Response({'success': False, 'message': 'Filing already submitted'}, status=400)
        
        filing.status = 'submitted'
        filing.submitted_at = timezone.now()
        filing.save()
        
        return Response({'success': True, 'message': 'Filing submitted for review'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsRegistryOrAdmin])
    def approve(self, request, pk=None):
        """Approve filing."""
        from django.utils import timezone
        filing = self.get_object()
        
        filing.status = 'approved'
        filing.reviewed_at = timezone.now()
        filing.reviewed_by = request.user
        filing.filing_number = request.data.get('filing_number', '')
        filing.save()
        
        # Send notification
        from apps.notifications.tasks import notify_filing_approved
        # notify_filing_approved.delay(str(filing.id))
        
        return Response({'success': True, 'message': 'Filing approved'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsRegistryOrAdmin])
    def reject(self, request, pk=None):
        """Reject filing."""
        from django.utils import timezone
        filing = self.get_object()
        
        filing.status = 'rejected'
        filing.reviewed_at = timezone.now()
        filing.reviewed_by = request.user
        filing.status_note = request.data.get('reason', '')
        filing.save()
        
        return Response({'success': True, 'message': 'Filing rejected'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsRegistryOrAdmin])
    def request_corrections(self, request, pk=None):
        """Request corrections."""
        filing = self.get_object()
        filing.status = 'corrections_required'
        filing.status_note = request.data.get('corrections', '')
        filing.save()
        
        return Response({'success': True, 'message': 'Corrections requested'})
