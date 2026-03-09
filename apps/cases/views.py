"""
Views for cases endpoints.
"""
from django.db.models import Q, F
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from apps.common.permissions import CanManageCourt, IsOwnerOrAdmin
from apps.common.pagination import StandardResultsSetPagination
from apps.authentication.models import UserFollowing, UserActivity
from .models import Case, CaseHearing, CaseDocument, CaseNote, CaseTimeline
from .serializers import (
    CaseListSerializer,
    CaseDetailSerializer,
    CaseCreateSerializer,
    CaseUpdateSerializer,
    CaseHearingSerializer,
    CaseDocumentSerializer,
    CaseNoteSerializer,
    CaseTimelineSerializer,
    CaseSearchSerializer,
    CaseSuggestionSerializer,
)
from .filters import CaseFilter


@extend_schema_view(
    list=extend_schema(
        tags=['Cases'],
        summary='List cases',
        parameters=[
            OpenApiParameter(name='court', description='Filter by court ID'),
            OpenApiParameter(name='judge', description='Filter by judge ID'),
            OpenApiParameter(name='case_type', description='Filter by case type'),
            OpenApiParameter(name='status', description='Filter by status'),
            OpenApiParameter(name='search', description='Search cases'),
        ]
    ),
    retrieve=extend_schema(tags=['Cases'], summary='Get case details'),
    create=extend_schema(tags=['Cases'], summary='Create case'),
    update=extend_schema(tags=['Cases'], summary='Update case'),
    partial_update=extend_schema(tags=['Cases'], summary='Partially update case'),
    destroy=extend_schema(tags=['Cases'], summary='Delete case'),
)
class CaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cases.
    """
    queryset = Case.objects.filter(is_deleted=False)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CaseFilter
    search_fields = ['case_number', 'parties', 'applicant', 'respondent', 'subject_matter']
    ordering_fields = ['case_number', 'filing_date', 'next_hearing_date', 'created_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'search', 'suggestions', 'timeline', 'hearings']:
            return [AllowAny()]
        return [CanManageCourt()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CaseListSerializer
        if self.action == 'create':
            return CaseCreateSerializer
        if self.action in ['update', 'partial_update']:
            return CaseUpdateSerializer
        if self.action == 'search':
            return CaseSearchSerializer
        return CaseDetailSerializer
    
    def get_queryset(self):
        return super().get_queryset().select_related('court', 'division', 'judge')
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        
        # Log view activity
        if request.user.is_authenticated:
            UserActivity.objects.create(
                user=request.user,
                activity_type='view_case',
                details={'case_id': str(kwargs.get('pk'))}
            )
        
        return response
    
    @extend_schema(tags=['Cases'], summary='Search cases')
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced case search."""
        queryset = self.get_queryset()
        
        # Get search parameters
        q = request.query_params.get('q', '')
        case_number = request.query_params.get('case_number', '')
        parties = request.query_params.get('parties', '')
        court = request.query_params.get('court')
        judge = request.query_params.get('judge')
        case_type = request.query_params.get('case_type')
        status_param = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Build query
        if q:
            queryset = queryset.filter(
                Q(case_number__icontains=q) |
                Q(parties__icontains=q) |
                Q(applicant__icontains=q) |
                Q(respondent__icontains=q) |
                Q(subject_matter__icontains=q)
            )
        
        if case_number:
            queryset = queryset.filter(case_number__icontains=case_number)
        
        if parties:
            queryset = queryset.filter(
                Q(parties__icontains=parties) |
                Q(applicant__icontains=parties) |
                Q(respondent__icontains=parties)
            )
        
        if court:
            queryset = queryset.filter(court_id=court)
        
        if judge:
            queryset = queryset.filter(judge_id=judge)
        
        if case_type:
            queryset = queryset.filter(case_type=case_type)
        
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        if date_from:
            queryset = queryset.filter(filing_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(filing_date__lte=date_to)
        
        # Log search activity
        if request.user.is_authenticated:
            UserActivity.objects.create(
                user=request.user,
                activity_type='search',
                details={'query': q, 'filters': request.query_params.dict()}
            )
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CaseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CaseListSerializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})
    
    @extend_schema(tags=['Cases'], summary='Get case suggestions')
    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """Get case suggestions based on partial input (fuzzy search)."""
        q = request.query_params.get('q', '')
        
        if len(q) < 2:
            return Response({'success': True, 'data': []})
        
        # Simple fuzzy search using icontains
        queryset = self.get_queryset().filter(
            Q(case_number__icontains=q) |
            Q(parties__icontains=q)
        )[:10]
        
        suggestions = []
        for case in queryset:
            suggestions.append({
                'id': str(case.id),
                'case_number': case.case_number,
                'parties': case.parties[:100],
                'score': 1.0  # Simplified scoring
            })
        
        return Response({'success': True, 'data': suggestions})
    
    @extend_schema(tags=['Cases'], summary='Follow a case')
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        """Follow a case for updates."""
        case = self.get_object()
        
        following, created = UserFollowing.objects.get_or_create(
            user=request.user,
            follow_type='case',
            object_id=case.id,
            defaults={'notifications_enabled': True}
        )
        
        if not created:
            return Response({
                'success': False,
                'message': 'Already following this case.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update follower count
        Case.objects.filter(pk=case.pk).update(
            follower_count=F('follower_count') + 1
        )
        
        return Response({
            'success': True,
            'message': f'Now following case {case.case_number}',
        })
    
    @extend_schema(tags=['Cases'], summary='Unfollow a case')
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        """Unfollow a case."""
        case = self.get_object()
        
        deleted, _ = UserFollowing.objects.filter(
            user=request.user,
            follow_type='case',
            object_id=case.id,
        ).delete()
        
        if not deleted:
            return Response({
                'success': False,
                'message': 'Not following this case.',
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update follower count
        Case.objects.filter(pk=case.pk).update(
            follower_count=F('follower_count') - 1
        )
        
        return Response({
            'success': True,
            'message': f'Unfollowed case {case.case_number}',
        })
    
    @extend_schema(tags=['Cases'], summary='Get case timeline')
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get complete timeline for a case."""
        case = self.get_object()
        timeline = case.timeline.all()
        
        serializer = CaseTimelineSerializer(timeline, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })
    
    @extend_schema(tags=['Cases'], summary='Get case hearings')
    @action(detail=True, methods=['get'])
    def hearings(self, request, pk=None):
        """Get all hearings for a case."""
        case = self.get_object()
        hearings = case.hearings.all()
        
        serializer = CaseHearingSerializer(hearings, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })
    
    @extend_schema(tags=['Cases'], summary='Get case documents')
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get all documents for a case."""
        case = self.get_object()
        
        # Filter by visibility
        if request.user.is_authenticated:
            documents = case.documents.filter(is_deleted=False)
        else:
            documents = case.documents.filter(is_deleted=False, is_public=True)
        
        serializer = CaseDocumentSerializer(documents, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })


@extend_schema_view(
    list=extend_schema(tags=['Cases'], summary='List case hearings'),
    retrieve=extend_schema(tags=['Cases'], summary='Get hearing details'),
    create=extend_schema(tags=['Cases'], summary='Create hearing record'),
    update=extend_schema(tags=['Cases'], summary='Update hearing'),
)
class CaseHearingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing case hearings.
    """
    queryset = CaseHearing.objects.all()
    serializer_class = CaseHearingSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['case', 'date', 'outcome']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [CanManageCourt()]
    
    def perform_create(self, serializer):
        hearing = serializer.save()
        
        # Update case statistics
        case = hearing.case
        case.total_hearings = case.hearings.count()
        case.last_hearing_date = hearing.date
        if hearing.next_date:
            case.next_hearing_date = hearing.next_date
        if hearing.outcome == 'adjourned':
            case.total_adjournments += 1
        case.save()
        
        # Create timeline entry
        CaseTimeline.objects.create(
            case=case,
            event_type='hearing',
            event_date=hearing.created_at,
            title=f'Hearing on {hearing.date}',
            description=hearing.outcome_notes or f'Outcome: {hearing.get_outcome_display()}',
            hearing=hearing
        )


@extend_schema_view(
    list=extend_schema(tags=['Cases'], summary='List user case notes'),
    create=extend_schema(tags=['Cases'], summary='Create case note'),
    retrieve=extend_schema(tags=['Cases'], summary='Get case note'),
    update=extend_schema(tags=['Cases'], summary='Update case note'),
    destroy=extend_schema(tags=['Cases'], summary='Delete case note'),
)
class CaseNoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user case notes.
    """
    serializer_class = CaseNoteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return CaseNote.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
