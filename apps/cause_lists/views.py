"""
Views for cause lists endpoints.
"""
from datetime import date, timedelta
from django.db.models import Count, Q
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from apps.common.permissions import CanUploadCauseList, IsRegistryOrAdmin
from apps.common.pagination import CauseListPagination, StandardResultsSetPagination
from .models import CauseList, CauseListEntry, CauseListChange, CauseListSubscription, CauseListImage
from .serializers import (
    CauseListSerializer,
    CauseListListSerializer,
    CauseListCreateSerializer,
    CauseListUpdateSerializer,
    CauseListStatusUpdateSerializer,
    CauseListEntrySerializer,
    CauseListEntryCreateSerializer,
    CauseListChangeSerializer,
    CauseListSubscriptionSerializer,
    CauseListUploadSerializer,
    CauseListImageSerializer,
    DailyCauseListSerializer,
)
from .filters import CauseListFilter


@extend_schema_view(
    list=extend_schema(
        tags=['Cause Lists'],
        summary='List cause lists',
        parameters=[
            OpenApiParameter(name='court', description='Filter by court ID'),
            OpenApiParameter(name='judge', description='Filter by judge ID'),
            OpenApiParameter(name='date', description='Filter by date (YYYY-MM-DD)'),
            OpenApiParameter(name='status', description='Filter by status'),
        ]
    ),
    retrieve=extend_schema(tags=['Cause Lists'], summary='Get cause list details'),
    create=extend_schema(tags=['Cause Lists'], summary='Create cause list'),
    update=extend_schema(tags=['Cause Lists'], summary='Update cause list'),
    partial_update=extend_schema(tags=['Cause Lists'], summary='Partially update cause list'),
    destroy=extend_schema(tags=['Cause Lists'], summary='Delete cause list'),
)
class CauseListViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cause lists.
    
    This is the core API for Cynosure's cause list functionality.
    """
    queryset = CauseList.objects.filter(is_deleted=False)
    pagination_class = CauseListPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CauseListFilter
    ordering_fields = ['date', 'created_at', 'court__name']
    ordering = ['-date', 'court__name']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'daily', 'by_judge', 'by_court', 'future', 'changes']:
            return [AllowAny()]
        return [CanUploadCauseList()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CauseListListSerializer
        if self.action == 'create':
            return CauseListCreateSerializer
        if self.action in ['update', 'partial_update']:
            return CauseListUpdateSerializer
        if self.action == 'update_status':
            return CauseListStatusUpdateSerializer
        if self.action == 'upload':
            return CauseListUploadSerializer
        return CauseListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'court', 'judge', 'panel', 'courtroom'
        )
        
        if self.action == 'list':
            # Only show published lists to public
            if not self.request.user.is_authenticated or \
               self.request.user.user_type not in ['registry_staff', 'super_admin']:
                queryset = queryset.filter(status__in=['published', 'sitting', 'adjourned', 'risen'])
        
        return queryset
    
    def perform_create(self, serializer):
        cause_list = serializer.save(
            published_by=self.request.user,
            published_at=timezone.now()
        )
        
        # Log change
        CauseListChange.objects.create(
            cause_list=cause_list,
            change_type='created',
            changed_by=self.request.user,
            changes={'action': 'created'}
        )
        
        # Trigger notifications
        from apps.notifications.tasks import notify_new_cause_list
        notify_new_cause_list.delay(str(cause_list.id))
    
    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_data = CauseListSerializer(old_instance).data
        
        instance = serializer.save()
        instance.version += 1
        instance.save(update_fields=['version'])
        
        # Track changes
        new_data = CauseListSerializer(instance).data
        changes = {}
        for field in ['status', 'courtroom', 'start_time', 'end_time']:
            if old_data.get(field) != new_data.get(field):
                changes[field] = {
                    'old': old_data.get(field),
                    'new': new_data.get(field)
                }
        
        if changes:
            change_type = 'status_changed' if 'status' in changes else 'updated'
            CauseListChange.objects.create(
                cause_list=instance,
                change_type=change_type,
                changes=changes,
                changed_by=self.request.user
            )
            
            # Trigger notifications
            from apps.notifications.tasks import notify_cause_list_change
            notify_cause_list_change.delay(str(instance.id), changes)
    
    @extend_schema(tags=['Cause Lists'], summary='Get daily summary')
    @action(detail=False, methods=['get'])
    def daily(self, request):
        """Get cause list summary for a specific date."""
        date_str = request.query_params.get('date', str(date.today()))
        
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cache key
        cache_key = f'cause_list:daily:{date_str}'
        cached = cache.get(cache_key)
        
        if cached:
            return Response({'success': True, 'data': cached})
        
        cause_lists = self.get_queryset().filter(date=target_date)
        
        # Group by status
        by_status = dict(
            cause_lists.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )
        
        # Get court summary
        courts = []
        court_groups = cause_lists.values('court__id', 'court__name').annotate(
            count=Count('id')
        )
        for court_group in court_groups:
            court_lists = cause_lists.filter(court_id=court_group['court__id'])
            courts.append({
                'court_id': str(court_group['court__id']),
                'court_name': court_group['court__name'],
                'total_lists': court_group['count'],
                'lists': CauseListListSerializer(court_lists, many=True).data
            })
        
        data = {
            'date': str(target_date),
            'total_lists': cause_lists.count(),
            'by_status': by_status,
            'courts': courts,
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, data, timeout=300)
        
        return Response({'success': True, 'data': data})
    
    @extend_schema(tags=['Cause Lists'], summary='Get cause lists by judge')
    @action(detail=False, methods=['get'])
    def by_judge(self, request):
        """Get cause lists for a specific judge."""
        judge_id = request.query_params.get('judge_id')
        if not judge_id:
            return Response({
                'success': False,
                'message': 'judge_id parameter is required.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Default to today and future
        start_date = request.query_params.get('start_date', str(date.today()))
        days = int(request.query_params.get('days', 14))
        
        try:
            start = date.fromisoformat(start_date)
        except ValueError:
            start = date.today()
        
        end = start + timedelta(days=days)
        
        cause_lists = self.get_queryset().filter(
            judge_id=judge_id,
            date__gte=start,
            date__lte=end
        ).order_by('date')
        
        serializer = CauseListListSerializer(cause_lists, many=True)
        
        return Response({
            'success': True,
            'data': {
                'judge_id': judge_id,
                'start_date': str(start),
                'end_date': str(end),
                'count': cause_lists.count(),
                'cause_lists': serializer.data,
            }
        })
    
    @extend_schema(tags=['Cause Lists'], summary='Get cause lists by court')
    @action(detail=False, methods=['get'])
    def by_court(self, request):
        """Get cause lists for a specific court."""
        court_id = request.query_params.get('court_id')
        if not court_id:
            return Response({
                'success': False,
                'message': 'court_id parameter is required.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        start_date = request.query_params.get('start_date', str(date.today()))
        days = int(request.query_params.get('days', 14))
        
        try:
            start = date.fromisoformat(start_date)
        except ValueError:
            start = date.today()
        
        end = start + timedelta(days=days)
        
        cause_lists = self.get_queryset().filter(
            court_id=court_id,
            date__gte=start,
            date__lte=end
        ).order_by('date', 'judge__last_name')
        
        serializer = CauseListListSerializer(cause_lists, many=True)
        
        return Response({
            'success': True,
            'data': {
                'court_id': court_id,
                'start_date': str(start),
                'end_date': str(end),
                'count': cause_lists.count(),
                'cause_lists': serializer.data,
            }
        })
    
    @extend_schema(tags=['Cause Lists'], summary='Get future cause lists')
    @action(detail=False, methods=['get'])
    def future(self, request):
        """Get all future cause lists."""
        days = int(request.query_params.get('days', 14))
        today = date.today()
        end_date = today + timedelta(days=days)
        
        cause_lists = self.get_queryset().filter(
            date__gte=today,
            date__lte=end_date
        ).order_by('date', 'court__name')
        
        page = self.paginate_queryset(cause_lists)
        if page is not None:
            serializer = CauseListListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CauseListListSerializer(cause_lists, many=True)
        return Response({'success': True, 'data': serializer.data})
    
    @extend_schema(tags=['Cause Lists'], summary='Update cause list status')
    @action(detail=True, methods=['post'], permission_classes=[IsRegistryOrAdmin])
    def update_status(self, request, pk=None):
        """Update the status of a cause list."""
        cause_list = self.get_object()
        serializer = CauseListStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        old_status = cause_list.status
        
        cause_list.status = serializer.validated_data['status']
        cause_list.status_note = serializer.validated_data.get('status_note', '')
        cause_list.adjournment_reason = serializer.validated_data.get('adjournment_reason', '')
        cause_list.not_sitting_reason = serializer.validated_data.get('not_sitting_reason', '')
        cause_list.version += 1
        cause_list.save()
        
        # Log change
        CauseListChange.objects.create(
            cause_list=cause_list,
            change_type='status_changed',
            field_name='status',
            old_value=old_status,
            new_value=cause_list.status,
            changed_by=request.user
        )
        
        # Trigger notifications
        from apps.notifications.tasks import notify_cause_list_status_change
        notify_cause_list_status_change.delay(str(cause_list.id), old_status, cause_list.status)
        
        return Response({
            'success': True,
            'message': f'Status updated to {cause_list.get_status_display()}',
            'data': CauseListSerializer(cause_list).data,
        })
    
    @extend_schema(tags=['Cause Lists'], summary='Upload cause list PDF')
    @action(
        detail=False, 
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[CanUploadCauseList]
    )
    def upload(self, request):
        """Upload a cause list PDF for parsing."""
        serializer = CauseListUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create cause list with PDF
        from apps.courts.models import Court
        from apps.judges.models import Judge
        from apps.courts.models import Panel
        
        court = Court.objects.get(id=serializer.validated_data['court'])
        judge = None
        panel = None
        
        if serializer.validated_data.get('judge'):
            judge = Judge.objects.get(id=serializer.validated_data['judge'])
        if serializer.validated_data.get('panel'):
            panel = Panel.objects.get(id=serializer.validated_data['panel'])
        
        cause_list = CauseList.objects.create(
            court=court,
            judge=judge,
            panel=panel,
            date=serializer.validated_data['date'],
            pdf_file=serializer.validated_data['pdf_file'],
            source='upload',
            status='draft',
            published_by=request.user,
            pdf_uploaded_at=timezone.now()
        )
        
        # Trigger PDF parsing task
        from apps.scraping.tasks import parse_cause_list_pdf
        parse_cause_list_pdf.delay(str(cause_list.id))
        
        return Response({
            'success': True,
            'message': 'PDF uploaded. Parsing in progress.',
            'data': CauseListSerializer(cause_list).data,
        }, status=status.HTTP_201_CREATED)
    
    @extend_schema(tags=['Cause Lists'], summary='Get cause list changes')
    @action(detail=True, methods=['get'])
    def changes(self, request, pk=None):
        """Get change history for a cause list."""
        cause_list = self.get_object()
        changes = cause_list.changes.all()[:50]

        serializer = CauseListChangeSerializer(changes, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    @extend_schema(tags=['Cause Lists'], summary='Upload cause list images')
    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[CanUploadCauseList],
        url_path='images',
    )
    def upload_images(self, request, pk=None):
        """
        Upload one or more images for a cause list.
        Staff snap photos of the physical list at court and upload them here.
        Each image is automatically compressed and a thumbnail is generated.

        Accepts multipart form data with:
          - images: one or more image files (JPEG / PNG / WEBP / HEIC)
          - page_start: (optional int) starting page number for this batch (default: next available)
        """
        from django.core.files.base import ContentFile
        from .image_utils import process_cause_list_image

        cause_list = self.get_object()
        files = request.FILES.getlist('images')

        if not files:
            return Response(
                {'success': False, 'message': 'No images provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine starting page number
        next_page = cause_list.images.filter(is_deleted=False).count() + 1
        try:
            page_start = int(request.data.get('page_start', next_page))
        except (TypeError, ValueError):
            page_start = next_page

        created = []
        errors = []

        for i, file_obj in enumerate(files):
            try:
                result = process_cause_list_image(file_obj)
            except Exception as exc:
                errors.append({'file': file_obj.name, 'error': str(exc)})
                continue

            page_number = page_start + i
            base_name = f"cl_{cause_list.id}_p{page_number:03d}.jpg"
            thumb_name = f"thumb_{cause_list.id}_p{page_number:03d}.jpg"

            img_instance = CauseListImage(
                cause_list=cause_list,
                page_number=page_number,
                width=result['width'],
                height=result['height'],
                file_size=result['file_size'],
                uploaded_by=request.user,
            )
            img_instance.image.save(base_name, ContentFile(result['image_io'].read()), save=False)
            img_instance.thumbnail.save(thumb_name, ContentFile(result['thumb_io'].read()), save=False)
            img_instance.save()
            created.append(img_instance)

        serializer = CauseListImageSerializer(created, many=True, context={'request': request})
        response_data = {
            'success': True,
            'uploaded': len(created),
            'images': serializer.data,
        }
        if errors:
            response_data['errors'] = errors

        http_status = status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST
        return Response(response_data, status=http_status)

    @extend_schema(tags=['Cause Lists'], summary='Delete a cause list image')
    @action(
        detail=True,
        methods=['delete'],
        permission_classes=[CanUploadCauseList],
        url_path=r'images/(?P<image_id>[^/.]+)',
    )
    def delete_image(self, request, pk=None, image_id=None):
        """Delete a single image from a cause list (soft delete)."""
        cause_list = self.get_object()
        try:
            image = cause_list.images.get(id=image_id, is_deleted=False)
        except CauseListImage.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Image not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        image.soft_delete()
        return Response({'success': True, 'message': 'Image deleted.'})

    @extend_schema(tags=['Cause Lists'], summary='List images for a cause list')
    @action(
        detail=True,
        methods=['get'],
        url_path='images',
        permission_classes=[AllowAny],
    )
    def list_images(self, request, pk=None):
        """Return all images for a cause list ordered by page number."""
        cause_list = self.get_object()
        images = cause_list.images.filter(is_deleted=False).order_by('page_number')
        serializer = CauseListImageSerializer(images, many=True, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


@extend_schema_view(
    list=extend_schema(tags=['Cause Lists'], summary='List cause list entries'),
    retrieve=extend_schema(tags=['Cause Lists'], summary='Get entry details'),
    create=extend_schema(tags=['Cause Lists'], summary='Add entry to cause list'),
    update=extend_schema(tags=['Cause Lists'], summary='Update entry'),
    destroy=extend_schema(tags=['Cause Lists'], summary='Remove entry'),
)
class CauseListEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cause list entries.
    """
    queryset = CauseListEntry.objects.filter(is_deleted=False)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['cause_list', 'case_number', 'status', 'case_type']
    search_fields = ['case_number', 'parties', 'applicant', 'respondent']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsRegistryOrAdmin()]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CauseListEntryCreateSerializer
        return CauseListEntrySerializer
    
    def perform_create(self, serializer):
        entry = serializer.save()
        entry.cause_list.update_case_count()
        
        # Log change
        CauseListChange.objects.create(
            cause_list=entry.cause_list,
            entry=entry,
            change_type='case_added',
            changed_by=self.request.user,
            changes={'case_number': entry.case_number}
        )
    
    def perform_destroy(self, instance):
        cause_list = instance.cause_list
        
        # Log change before delete
        CauseListChange.objects.create(
            cause_list=cause_list,
            change_type='case_removed',
            changed_by=self.request.user,
            changes={'case_number': instance.case_number}
        )
        
        instance.soft_delete()
        cause_list.update_case_count()


@extend_schema_view(
    list=extend_schema(tags=['Cause Lists'], summary='List subscriptions'),
    create=extend_schema(tags=['Cause Lists'], summary='Create subscription'),
    retrieve=extend_schema(tags=['Cause Lists'], summary='Get subscription'),
    update=extend_schema(tags=['Cause Lists'], summary='Update subscription'),
    destroy=extend_schema(tags=['Cause Lists'], summary='Delete subscription'),
)
class CauseListSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cause list subscriptions.
    """
    serializer_class = CauseListSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return CauseListSubscription.objects.filter(
            user=self.request.user,
            is_active=True
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
