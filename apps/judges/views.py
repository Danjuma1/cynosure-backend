"""
Views for judges endpoints.
"""
from datetime import date, timedelta
from django.db.models import Count, Q, F
from django.core.cache import cache
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from apps.common.permissions import CanManageCourt, IsRegistryOrAdmin
from apps.common.pagination import StandardResultsSetPagination
from apps.authentication.models import UserFollowing
from .models import Judge, JudgeAvailability, JudgeTransfer, JudgeLeave
from .serializers import (
    JudgeListSerializer,
    JudgeDetailSerializer,
    JudgeCreateUpdateSerializer,
    JudgeAvailabilitySerializer,
    JudgeAvailabilityCreateSerializer,
    JudgeTransferSerializer,
    JudgeLeaveSerializer,
    JudgeStatusUpdateSerializer,
    JudgeStatisticsSerializer,
)
from .filters import JudgeFilter


@extend_schema_view(
    list=extend_schema(
        tags=['Judges'],
        summary='List all judges',
        parameters=[
            OpenApiParameter(name='court', description='Filter by court ID'),
            OpenApiParameter(name='division', description='Filter by division ID'),
            OpenApiParameter(name='status', description='Filter by status'),
            OpenApiParameter(name='search', description='Search by name'),
        ]
    ),
    retrieve=extend_schema(tags=['Judges'], summary='Get judge details'),
    create=extend_schema(tags=['Judges'], summary='Create new judge (Admin only)'),
    update=extend_schema(tags=['Judges'], summary='Update judge (Admin only)'),
    partial_update=extend_schema(tags=['Judges'], summary='Partially update judge'),
    destroy=extend_schema(tags=['Judges'], summary='Delete judge (Admin only)'),
)
class JudgeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing judges.
    """
    queryset = Judge.objects.filter(is_deleted=False)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JudgeFilter
    search_fields = ['first_name', 'last_name', 'other_names']
    ordering_fields = ['last_name', 'first_name', 'appointment_date', 'follower_count']
    ordering = ['last_name', 'first_name']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'availability', 'statistics']:
            return [AllowAny()]
        return [CanManageCourt()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return JudgeListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return JudgeCreateUpdateSerializer
        if self.action == 'update_status':
            return JudgeStatusUpdateSerializer
        return JudgeDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('court', 'division', 'default_courtroom')
        
        if self.action == 'list':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @extend_schema(tags=['Judges'], summary='Get judge statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get overall judge statistics."""
        cache_key = 'judges:statistics'
        stats = cache.get(cache_key)
        
        if not stats:
            judges = Judge.objects.filter(is_deleted=False)
            
            stats = {
                'total_judges': judges.count(),
                'active_judges': judges.filter(status='active', is_active=True).count(),
                'judges_on_leave': judges.filter(status='on_leave').count(),
                'judges_by_court': dict(
                    judges.values('court__name')
                    .annotate(count=Count('id'))
                    .values_list('court__name', 'count')
                ),
                'judges_by_status': dict(
                    judges.values('status')
                    .annotate(count=Count('id'))
                    .values_list('status', 'count')
                ),
            }
            
            cache.set(cache_key, stats, timeout=3600)
        
        return Response({
            'success': True,
            'data': stats,
        })
    
    @extend_schema(tags=['Judges'], summary='Follow a judge')
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        """Follow a judge for updates."""
        judge = self.get_object()
        
        following, created = UserFollowing.objects.get_or_create(
            user=request.user,
            follow_type='judge',
            object_id=judge.id,
            defaults={'notifications_enabled': True}
        )
        
        if not created:
            return Response({
                'success': False,
                'message': 'Already following this judge.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update follower count
        Judge.objects.filter(pk=judge.pk).update(
            follower_count=F('follower_count') + 1
        )
        
        return Response({
            'success': True,
            'message': f'Now following {judge.formal_name}',
        })
    
    @extend_schema(tags=['Judges'], summary='Unfollow a judge')
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        """Unfollow a judge."""
        judge = self.get_object()
        
        deleted, _ = UserFollowing.objects.filter(
            user=request.user,
            follow_type='judge',
            object_id=judge.id,
        ).delete()
        
        if not deleted:
            return Response({
                'success': False,
                'message': 'Not following this judge.',
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update follower count
        Judge.objects.filter(pk=judge.pk).update(
            follower_count=F('follower_count') - 1
        )
        
        return Response({
            'success': True,
            'message': f'Unfollowed {judge.formal_name}',
        })
    
    @extend_schema(tags=['Judges'], summary='Get judge availability')
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Get availability for a specific judge."""
        judge = self.get_object()
        
        # Default to next 14 days
        days = int(request.query_params.get('days', 14))
        start_date = date.today()
        end_date = start_date + timedelta(days=days)
        
        availability = judge.availability_records.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        serializer = JudgeAvailabilitySerializer(availability, many=True)
        
        return Response({
            'success': True,
            'data': {
                'judge_id': str(judge.id),
                'judge_name': judge.formal_name,
                'default_sitting_days': judge.sitting_days,
                'default_sitting_time': {
                    'start': str(judge.sitting_time_start) if judge.sitting_time_start else None,
                    'end': str(judge.sitting_time_end) if judge.sitting_time_end else None,
                },
                'availability': serializer.data,
            }
        })
    
    @extend_schema(tags=['Judges'], summary='Update judge status')
    @action(detail=True, methods=['post'], permission_classes=[IsRegistryOrAdmin])
    def update_status(self, request, pk=None):
        """Update judge status."""
        judge = self.get_object()
        serializer = JudgeStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update judge
        judge.status = serializer.validated_data['status']
        judge.status_note = serializer.validated_data.get('status_note', '')
        judge.status_effective_from = serializer.validated_data.get('status_effective_from')
        judge.status_effective_until = serializer.validated_data.get('status_effective_until')
        judge.save()
        
        # Trigger notifications for status change
        from apps.notifications.tasks import notify_judge_status_change
        notify_judge_status_change.delay(str(judge.id), serializer.validated_data['status'])
        
        return Response({
            'success': True,
            'message': f'Status updated to {judge.get_status_display()}',
            'data': JudgeDetailSerializer(judge).data,
        })
    
    @extend_schema(tags=['Judges'], summary='Get judge cause lists')
    @action(detail=True, methods=['get'])
    def cause_lists(self, request, pk=None):
        """Get cause lists for a specific judge."""
        judge = self.get_object()
        
        from apps.cause_lists.models import CauseList
        from apps.cause_lists.serializers import CauseListSerializer
        
        # Default to future cause lists
        start_date = date.today()
        days = int(request.query_params.get('days', 14))
        end_date = start_date + timedelta(days=days)
        
        cause_lists = CauseList.objects.filter(
            judge=judge,
            date__gte=start_date,
            date__lte=end_date,
            is_deleted=False
        ).order_by('date')
        
        serializer = CauseListSerializer(cause_lists, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
        })


@extend_schema_view(
    list=extend_schema(tags=['Judges'], summary='List judge availability records'),
    create=extend_schema(tags=['Judges'], summary='Create availability record'),
    retrieve=extend_schema(tags=['Judges'], summary='Get availability record'),
    update=extend_schema(tags=['Judges'], summary='Update availability record'),
    destroy=extend_schema(tags=['Judges'], summary='Delete availability record'),
)
class JudgeAvailabilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing judge availability.
    """
    queryset = JudgeAvailability.objects.all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['judge', 'date', 'availability']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsRegistryOrAdmin()]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return JudgeAvailabilityCreateSerializer
        return JudgeAvailabilitySerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('judge', 'alternate_judge')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('date')


@extend_schema_view(
    list=extend_schema(tags=['Judges'], summary='List judge transfers'),
    create=extend_schema(tags=['Judges'], summary='Create transfer record (Admin only)'),
    retrieve=extend_schema(tags=['Judges'], summary='Get transfer details'),
)
class JudgeTransferViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing judge transfers.
    """
    queryset = JudgeTransfer.objects.all()
    serializer_class = JudgeTransferSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['judge', 'from_court', 'to_court']
    http_method_names = ['get', 'post']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [CanManageCourt()]
    
    def perform_create(self, serializer):
        transfer = serializer.save(created_by=self.request.user)
        
        # Update judge's court assignment
        judge = transfer.judge
        judge.court = transfer.to_court
        judge.division = transfer.to_division
        judge.status = 'active'
        judge.save()


@extend_schema_view(
    list=extend_schema(tags=['Judges'], summary='List judge leave records'),
    create=extend_schema(tags=['Judges'], summary='Create leave record'),
    retrieve=extend_schema(tags=['Judges'], summary='Get leave details'),
)
class JudgeLeaveViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing judge leave records.
    """
    queryset = JudgeLeave.objects.all()
    serializer_class = JudgeLeaveSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['judge', 'leave_type', 'is_approved']
    http_method_names = ['get', 'post', 'patch']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsRegistryOrAdmin()]
    
    @extend_schema(tags=['Judges'], summary='Approve leave request')
    @action(detail=True, methods=['post'], permission_classes=[CanManageCourt])
    def approve(self, request, pk=None):
        """Approve a leave request."""
        from django.utils import timezone
        
        leave = self.get_object()
        
        if leave.is_approved:
            return Response({
                'success': False,
                'message': 'Leave already approved.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        leave.is_approved = True
        leave.approved_by = request.user
        leave.approved_at = timezone.now()
        leave.save()
        
        # Update judge status
        leave.judge.status = 'on_leave'
        leave.judge.status_effective_from = leave.start_date
        leave.judge.status_effective_until = leave.end_date
        leave.judge.save()
        
        return Response({
            'success': True,
            'message': 'Leave approved.',
            'data': JudgeLeaveSerializer(leave).data,
        })
