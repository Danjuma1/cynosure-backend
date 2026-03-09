"""
Search app - Search functionality for cases, cause lists, and documents.
"""
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.common.pagination import SearchResultsPagination


class GlobalSearchView(APIView):
    """
    Global search across all content types.
    """
    permission_classes = [AllowAny]
    pagination_class = SearchResultsPagination
    
    @extend_schema(
        tags=['Search'],
        summary='Global search',
        parameters=[
            OpenApiParameter(name='q', description='Search query', required=True),
            OpenApiParameter(name='type', description='Content type filter (case, cause_list, document, judge, court)'),
            OpenApiParameter(name='court', description='Filter by court ID'),
            OpenApiParameter(name='date_from', description='Filter from date'),
            OpenApiParameter(name='date_to', description='Filter to date'),
        ]
    )
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        content_type = request.query_params.get('type', '')
        court_id = request.query_params.get('court')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if len(q) < 2:
            return Response({
                'success': False,
                'message': 'Search query must be at least 2 characters.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = {
            'cases': [],
            'cause_lists': [],
            'judges': [],
            'courts': [],
            'documents': [],
        }
        
        # Search cases
        if not content_type or content_type == 'case':
            from apps.cases.models import Case
            from apps.cases.serializers import CaseListSerializer
            
            cases = Case.objects.filter(
                Q(case_number__icontains=q) |
                Q(parties__icontains=q) |
                Q(applicant__icontains=q) |
                Q(respondent__icontains=q),
                is_deleted=False
            )
            if court_id:
                cases = cases.filter(court_id=court_id)
            results['cases'] = CaseListSerializer(cases[:20], many=True).data
        
        # Search cause lists
        if not content_type or content_type == 'cause_list':
            from apps.cause_lists.models import CauseListEntry
            from apps.cause_lists.serializers import CauseListEntrySerializer
            
            entries = CauseListEntry.objects.filter(
                Q(case_number__icontains=q) |
                Q(parties__icontains=q),
                is_deleted=False
            ).select_related('cause_list')
            if court_id:
                entries = entries.filter(cause_list__court_id=court_id)
            results['cause_lists'] = CauseListEntrySerializer(entries[:20], many=True).data
        
        # Search judges
        if not content_type or content_type == 'judge':
            from apps.judges.models import Judge
            from apps.judges.serializers import JudgeListSerializer
            
            judges = Judge.objects.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(other_names__icontains=q),
                is_deleted=False, is_active=True
            )
            if court_id:
                judges = judges.filter(court_id=court_id)
            results['judges'] = JudgeListSerializer(judges[:10], many=True).data
        
        # Search courts
        if not content_type or content_type == 'court':
            from apps.courts.models import Court
            from apps.courts.serializers import CourtListSerializer
            
            courts = Court.objects.filter(
                Q(name__icontains=q) | Q(code__icontains=q),
                is_deleted=False, is_active=True
            )
            results['courts'] = CourtListSerializer(courts[:10], many=True).data
        
        # Search documents
        if not content_type or content_type == 'document':
            from apps.repository.models import LegalDocument
            from apps.repository.serializers import LegalDocumentListSerializer
            
            docs = LegalDocument.objects.filter(
                Q(title__icontains=q) | Q(description__icontains=q),
                is_deleted=False, is_published=True
            )
            results['documents'] = LegalDocumentListSerializer(docs[:10], many=True).data
        
        # Log search activity
        if request.user.is_authenticated:
            from apps.authentication.models import UserActivity
            UserActivity.objects.create(
                user=request.user,
                activity_type='search',
                details={'query': q, 'type': content_type}
            )
        
        return Response({
            'success': True,
            'query': q,
            'results': results,
        })


class CaseSearchView(APIView):
    """Advanced case search with fuzzy matching."""
    permission_classes = [AllowAny]
    
    @extend_schema(tags=['Search'], summary='Search cases')
    def get(self, request):
        from apps.cases.models import Case
        from apps.cases.serializers import CaseListSerializer
        
        q = request.query_params.get('q', '')
        case_number = request.query_params.get('case_number', '')
        parties = request.query_params.get('parties', '')
        
        queryset = Case.objects.filter(is_deleted=False)
        
        if q:
            queryset = queryset.filter(
                Q(case_number__icontains=q) |
                Q(parties__icontains=q)
            )
        if case_number:
            queryset = queryset.filter(case_number__icontains=case_number)
        if parties:
            queryset = queryset.filter(parties__icontains=parties)
        
        serializer = CaseListSerializer(queryset[:50], many=True)
        return Response({'success': True, 'data': serializer.data})


class CauseListSearchView(APIView):
    """Search cause lists."""
    permission_classes = [AllowAny]
    
    @extend_schema(tags=['Search'], summary='Search cause lists')
    def get(self, request):
        from apps.cause_lists.models import CauseList
        from apps.cause_lists.serializers import CauseListListSerializer
        
        court_id = request.query_params.get('court')
        judge_id = request.query_params.get('judge')
        date = request.query_params.get('date')
        
        queryset = CauseList.objects.filter(
            is_deleted=False,
            status__in=['published', 'sitting']
        )
        
        if court_id:
            queryset = queryset.filter(court_id=court_id)
        if judge_id:
            queryset = queryset.filter(judge_id=judge_id)
        if date:
            queryset = queryset.filter(date=date)
        
        serializer = CauseListListSerializer(queryset[:50], many=True)
        return Response({'success': True, 'data': serializer.data})
