"""
Repository app - Legal document repository models and views.
"""
import uuid
from django.db import models
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from django_filters.rest_framework import DjangoFilterBackend
from apps.common.models import BaseModel, TimeStampedModel
from apps.common.pagination import StandardResultsSetPagination
from apps.common.permissions import IsRegistryOrAdmin


# ============== MODELS ==============

class DocumentCategory(BaseModel):
    """Categories for legal documents."""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Document categories'
    
    def __str__(self):
        return self.name


class LegalDocument(BaseModel):
    """Legal documents in the repository."""
    DOCUMENT_TYPE_CHOICES = [
        ('court_rule', 'Court Rule'),
        ('practice_direction', 'Practice Direction'),
        ('gazette', 'Gazette Extract'),
        ('law_report', 'Law Report'),
        ('form', 'Court Form'),
        ('template', 'Template'),
        ('constitution', 'Constitution'),
        ('statute', 'Statute'),
        ('regulation', 'Regulation'),
        ('circular', 'Circular'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    
    # Categorization
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    tags = models.JSONField(default=list, blank=True)
    
    # Court association
    court = models.ForeignKey('courts.Court', on_delete=models.SET_NULL, null=True, blank=True, related_name='repository_documents')
    
    # File
    file = models.FileField(upload_to='repository/')
    file_size = models.PositiveIntegerField(default=0)
    file_type = models.CharField(max_length=50, blank=True)
    
    # Dates
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    
    # Status
    is_published = models.BooleanField(default=True)
    is_current = models.BooleanField(default=True)
    supersedes = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='superseded_by')
    
    # Statistics
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    bookmark_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    source = models.CharField(max_length=255, blank=True)
    citation = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-publication_date', '-created_at']
        indexes = [
            models.Index(fields=['document_type', 'is_published']),
            models.Index(fields=['court', 'document_type']),
            models.Index(fields=['year']),
        ]
    
    def __str__(self):
        return self.title


class DocumentBookmark(TimeStampedModel):
    """User bookmarks for documents."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='document_bookmarks')
    document = models.ForeignKey(LegalDocument, on_delete=models.CASCADE, related_name='bookmarks')
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['user', 'document']
    
    def __str__(self):
        return f"{self.user.email} - {self.document.title}"


# ============== SERIALIZERS ==============

class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'slug', 'description', 'parent', 'order']


class LegalDocumentListSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    
    class Meta:
        model = LegalDocument
        fields = [
            'id', 'title', 'slug', 'document_type', 'document_type_display',
            'category', 'category_name', 'court', 'court_name',
            'effective_date', 'year', 'file', 'file_size',
            'view_count', 'download_count',
        ]


class LegalDocumentDetailSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    
    class Meta:
        model = LegalDocument
        fields = [
            'id', 'title', 'slug', 'description',
            'document_type', 'document_type_display',
            'category', 'category_name', 'tags',
            'court', 'court_name',
            'file', 'file_size', 'file_type',
            'effective_date', 'expiry_date', 'publication_date', 'year',
            'is_published', 'is_current',
            'view_count', 'download_count', 'bookmark_count',
            'source', 'citation',
            'created_at', 'updated_at',
        ]


class DocumentBookmarkSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    
    class Meta:
        model = DocumentBookmark
        fields = ['id', 'document', 'document_title', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


# ============== VIEWS ==============

class DocumentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for document categories."""
    queryset = DocumentCategory.objects.filter(is_deleted=False)
    serializer_class = DocumentCategorySerializer
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        category = self.get_object()
        documents = LegalDocument.objects.filter(
            category=category, is_deleted=False, is_published=True
        )
        serializer = LegalDocumentListSerializer(documents, many=True)
        return Response({'success': True, 'data': serializer.data})


class LegalDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for legal documents."""
    queryset = LegalDocument.objects.filter(is_deleted=False, is_published=True)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['document_type', 'category', 'court', 'year', 'is_current']
    search_fields = ['title', 'description', 'citation']
    ordering_fields = ['title', 'publication_date', 'view_count', 'download_count']
    lookup_field = 'slug'
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsRegistryOrAdmin()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LegalDocumentListSerializer
        return LegalDocumentDetailSerializer
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        LegalDocument.objects.filter(pk=instance.pk).update(view_count=models.F('view_count') + 1)
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def bookmark(self, request, slug=None):
        document = self.get_object()
        bookmark, created = DocumentBookmark.objects.get_or_create(
            user=request.user, document=document,
            defaults={'notes': request.data.get('notes', '')}
        )
        if not created:
            return Response({'success': False, 'message': 'Already bookmarked'}, status=400)
        
        LegalDocument.objects.filter(pk=document.pk).update(bookmark_count=models.F('bookmark_count') + 1)
        return Response({'success': True, 'message': 'Document bookmarked'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unbookmark(self, request, slug=None):
        document = self.get_object()
        deleted, _ = DocumentBookmark.objects.filter(user=request.user, document=document).delete()
        if not deleted:
            return Response({'success': False, 'message': 'Not bookmarked'}, status=404)
        
        LegalDocument.objects.filter(pk=document.pk).update(bookmark_count=models.F('bookmark_count') - 1)
        return Response({'success': True, 'message': 'Bookmark removed'})
    
    @action(detail=True, methods=['get'])
    def download(self, request, slug=None):
        document = self.get_object()
        LegalDocument.objects.filter(pk=document.pk).update(download_count=models.F('download_count') + 1)
        return Response({
            'success': True,
            'data': {'url': document.file.url, 'title': document.title}
        })


class DocumentBookmarkViewSet(viewsets.ModelViewSet):
    """ViewSet for user bookmarks."""
    serializer_class = DocumentBookmarkSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        return DocumentBookmark.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
