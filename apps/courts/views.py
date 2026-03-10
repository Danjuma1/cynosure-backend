"""
Views for courts endpoints.
"""
from django.db.models import Count, Q
from django.core.cache import cache
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from apps.common.permissions import CanManageCourt, IsSuperAdmin, IsRegistryOrAdmin
from apps.common.pagination import StandardResultsSetPagination
from apps.authentication.models import UserFollowing
from .models import Court, Division, Courtroom, Panel, CourtRule, CourtHoliday, CourtContact
from .serializers import (
    CourtListSerializer,
    CourtDetailSerializer,
    CourtCreateUpdateSerializer,
    DivisionListSerializer,
    DivisionDetailSerializer,
    DivisionCreateUpdateSerializer,
    CourtroomSerializer,
    PanelListSerializer,
    PanelDetailSerializer,
    PanelCreateUpdateSerializer,
    CourtRuleSerializer,
    CourtHolidaySerializer,
    CourtContactSerializer,
    CourtStatisticsSerializer,
)
from .filters import CourtFilter, DivisionFilter


@extend_schema_view(
    list=extend_schema(
        tags=['Courts'],
        summary='List all courts',
        parameters=[
            OpenApiParameter(name='state', description='Filter by state code'),
            OpenApiParameter(name='court_type', description='Filter by court type'),
            OpenApiParameter(name='search', description='Search courts by name'),
        ]
    ),
    retrieve=extend_schema(tags=['Courts'], summary='Get court details'),
    create=extend_schema(tags=['Courts'], summary='Create new court (Admin only)'),
    update=extend_schema(tags=['Courts'], summary='Update court (Admin only)'),
    partial_update=extend_schema(tags=['Courts'], summary='Partially update court (Admin only)'),
    destroy=extend_schema(tags=['Courts'], summary='Delete court (Admin only)'),
)
class CourtViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing courts.
    
    Provides CRUD operations for courts in the Nigerian judicial system.
    """
    queryset = Court.objects.filter(is_deleted=False)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CourtFilter
    search_fields = ['name', 'code', 'city']
    ordering_fields = ['name', 'created_at', 'follower_count']
    ordering = ['name']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'statistics', 'holidays', 'rules']:
            return [AllowAny()]
        return [CanManageCourt()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CourtListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return CourtCreateUpdateSerializer
        return CourtDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = queryset.filter(is_active=True)
        return queryset
    
    @extend_schema(tags=['Courts'], summary='Get court statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get overall court statistics."""
        cache_key = 'courts:statistics'
        stats = cache.get(cache_key)
        
        if not stats:
            courts = Court.objects.filter(is_deleted=False)
            
            stats = {
                'total_courts': courts.count(),
                'active_courts': courts.filter(is_active=True).count(),
                'courts_by_type': dict(
                    courts.values('court_type')
                    .annotate(count=Count('id'))
                    .values_list('court_type', 'count')
                ),
                'courts_by_state': dict(
                    courts.values('state')
                    .annotate(count=Count('id'))
                    .values_list('state', 'count')
                ),
                'total_judges': sum(c.total_judges for c in courts),
                'total_divisions': sum(c.total_divisions for c in courts),
            }
            
            cache.set(cache_key, stats, timeout=3600)  # 1 hour
        
        return Response({
            'success': True,
            'data': stats,
        })
    
    @extend_schema(tags=['Courts'], summary='Follow a court')
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        """Follow a court for updates."""
        court = self.get_object()
        
        following, created = UserFollowing.objects.get_or_create(
            user=request.user,
            follow_type='court',
            object_id=court.id,
            defaults={'notifications_enabled': True}
        )
        
        if not created:
            return Response({
                'success': False,
                'message': 'Already following this court.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update follower count
        Court.objects.filter(pk=court.pk).update(
            follower_count=models.F('follower_count') + 1
        )
        
        return Response({
            'success': True,
            'message': f'Now following {court.name}',
        })
    
    @extend_schema(tags=['Courts'], summary='Unfollow a court')
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        """Unfollow a court."""
        court = self.get_object()
        
        deleted, _ = UserFollowing.objects.filter(
            user=request.user,
            follow_type='court',
            object_id=court.id,
        ).delete()
        
        if not deleted:
            return Response({
                'success': False,
                'message': 'Not following this court.',
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update follower count
        Court.objects.filter(pk=court.pk).update(
            follower_count=models.F('follower_count') - 1
        )
        
        return Response({
            'success': True,
            'message': f'Unfollowed {court.name}',
        })
    
    @extend_schema(tags=['Courts'], summary='Get court holidays')
    @action(detail=True, methods=['get'])
    def holidays(self, request, pk=None):
        """Get holidays for a specific court."""
        court = self.get_object()
        holidays = court.holidays.all()
        
        # Filter by year if provided
        year = request.query_params.get('year')
        if year:
            holidays = holidays.filter(start_date__year=year)
        
        serializer = CourtHolidaySerializer(holidays, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })
    
    @extend_schema(tags=['Courts'], summary='Get court rules')
    @action(detail=True, methods=['get'])
    def rules(self, request, pk=None):
        """Get rules for a specific court."""
        court = self.get_object()
        rules = court.rules.filter(is_current=True)
        
        # Filter by type if provided
        rule_type = request.query_params.get('type')
        if rule_type:
            rules = rules.filter(rule_type=rule_type)
        
        serializer = CourtRuleSerializer(rules, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })
    
    @extend_schema(tags=['Courts'], summary='Get court divisions')
    @action(detail=True, methods=['get'])
    def divisions(self, request, pk=None):
        """Get divisions for a specific court."""
        court = self.get_object()
        divisions = court.divisions.filter(is_active=True)
        
        serializer = DivisionListSerializer(divisions, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })


@extend_schema_view(
    list=extend_schema(tags=['Courts'], summary='List divisions'),
    retrieve=extend_schema(tags=['Courts'], summary='Get division details'),
    create=extend_schema(tags=['Courts'], summary='Create division (Admin only)'),
    update=extend_schema(tags=['Courts'], summary='Update division (Admin only)'),
    partial_update=extend_schema(tags=['Courts'], summary='Partially update division'),
    destroy=extend_schema(tags=['Courts'], summary='Delete division (Admin only)'),
)
class DivisionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing court divisions.
    """
    queryset = Division.objects.filter(is_deleted=False)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = DivisionFilter
    search_fields = ['name', 'code']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [CanManageCourt()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DivisionListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return DivisionCreateUpdateSerializer
        return DivisionDetailSerializer


@extend_schema_view(
    list=extend_schema(tags=['Courts'], summary='List courtrooms'),
    retrieve=extend_schema(tags=['Courts'], summary='Get courtroom details'),
    create=extend_schema(tags=['Courts'], summary='Create courtroom (Admin only)'),
    update=extend_schema(tags=['Courts'], summary='Update courtroom (Admin only)'),
    destroy=extend_schema(tags=['Courts'], summary='Delete courtroom (Admin only)'),
)
class CourtroomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing courtrooms.
    """
    queryset = Courtroom.objects.filter(is_deleted=False, is_active=True)
    serializer_class = CourtroomSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['court', 'division', 'is_active']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [CanManageCourt()]


@extend_schema_view(
    list=extend_schema(tags=['Courts'], summary='List panels'),
    retrieve=extend_schema(tags=['Courts'], summary='Get panel details'),
    create=extend_schema(tags=['Courts'], summary='Create panel (Admin only)'),
    update=extend_schema(tags=['Courts'], summary='Update panel (Admin only)'),
    destroy=extend_schema(tags=['Courts'], summary='Delete panel (Admin only)'),
)
class PanelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing court panels (Appeal Courts).
    """
    queryset = Panel.objects.filter(is_deleted=False)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['court', 'is_active']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [CanManageCourt()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PanelListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return PanelCreateUpdateSerializer
        return PanelDetailSerializer
    
    @extend_schema(tags=['Courts'], summary='Get panel members')
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get members of a specific panel."""
        panel = self.get_object()
        
        # Fetch judge details for panel members
        from apps.judges.models import Judge
        from apps.judges.serializers import JudgeListSerializer
        
        judge_ids = panel.member_ids or []
        if panel.presiding_judge_id:
            judge_ids = [str(panel.presiding_judge_id)] + judge_ids
        
        judges = Judge.objects.filter(id__in=judge_ids)
        serializer = JudgeListSerializer(judges, many=True)
        
        return Response({
            'success': True,
            'data': {
                'presiding_judge_id': panel.presiding_judge_id,
                'members': serializer.data,
            }
        })


@extend_schema_view(
    list=extend_schema(tags=['Courts'], summary='List court rules'),
    retrieve=extend_schema(tags=['Courts'], summary='Get court rule details'),
    create=extend_schema(tags=['Courts'], summary='Upload court rule (Admin only)'),
    destroy=extend_schema(tags=['Courts'], summary='Delete court rule (Admin only)'),
)
class CourtRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing court rules and practice directions.
    """
    queryset = CourtRule.objects.filter(is_deleted=False)
    serializer_class = CourtRuleSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['court', 'rule_type', 'is_current']
    search_fields = ['title', 'description']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsRegistryOrAdmin()]


# Import models for the F expression
from django.db import models
