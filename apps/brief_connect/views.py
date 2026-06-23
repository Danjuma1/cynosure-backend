"""
Views for Brief Connect endpoints.
"""
import logging
from django.db.models import Q, Avg
from django.utils import timezone
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from apps.common.pagination import StandardResultsSetPagination
from .models import BriefRequest, BriefApplication, BriefEngagement, BriefReview
from .serializers import (
    BriefRequestSerializer,
    BriefRequestListSerializer,
    BriefRequestCreateSerializer,
    BriefRequestUpdateSerializer,
    BriefApplicationSerializer,
    BriefApplicationCreateSerializer,
    BriefEngagementSerializer,
    BriefReviewSerializer,
)
from .filters import BriefRequestFilter

logger = logging.getLogger(__name__)


def _is_lawyer(user):
    return user.is_authenticated and user.user_type in ('lawyer', 'firm_admin')


def _try_dispatch(task, *args):
    """Fire a Celery task without crashing the response if the broker is down."""
    try:
        task.delay(*args)
    except Exception as exc:
        logger.warning('Brief Connect: could not dispatch task %s: %s', task.name, exc)


@extend_schema_view(
    list=extend_schema(tags=['Brief Connect'], summary='Browse open brief requests'),
    retrieve=extend_schema(tags=['Brief Connect'], summary='Get brief request detail'),
    create=extend_schema(tags=['Brief Connect'], summary='Post a new brief request'),
    update=extend_schema(tags=['Brief Connect'], summary='Update brief request'),
    partial_update=extend_schema(tags=['Brief Connect'], summary='Partially update brief request'),
    destroy=extend_schema(tags=['Brief Connect'], summary='Cancel brief request'),
)
class BriefRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing brief requests.
    All verified lawyers can browse and post. Only the requester can manage their own.
    """
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BriefRequestFilter
    search_fields = ['case_number', 'parties', 'instructions', 'court__name']
    ordering_fields = ['hearing_date', 'created_at', 'offered_fee']
    ordering = ['-created_at']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BriefRequest.objects.filter(is_deleted=False).select_related(
            'requester', 'court', 'judge'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return BriefRequestListSerializer
        if self.action == 'create':
            return BriefRequestCreateSerializer
        if self.action in ('update', 'partial_update'):
            return BriefRequestUpdateSerializer
        return BriefRequestSerializer

    def create(self, request, *args, **kwargs):
        if not _is_lawyer(request.user):
            return Response(
                {'success': False, 'message': 'Only lawyers can post brief requests.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        req = serializer.save()
        from apps.brief_connect.tasks import notify_brief_request_posted
        _try_dispatch(notify_brief_request_posted, str(req.id))

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.requester != request.user:
            return Response(
                {'success': False, 'message': 'Only the requester can edit this request.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if instance.status != 'open':
            return Response(
                {'success': False, 'message': 'Only open requests can be edited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.requester != request.user:
            return Response(
                {'success': False, 'message': 'Only the requester can cancel this request.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if instance.status not in ('open', 'accepted'):
            return Response(
                {'success': False, 'message': 'Only open or accepted requests can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.status = 'cancelled'
        instance.save(update_fields=['status', 'updated_at'])
        return Response({'success': True, 'message': 'Brief request cancelled.'})

    # ── Custom actions ────────────────────────────────────────────────────────

    @extend_schema(tags=['Brief Connect'], summary='My posted brief requests')
    @action(detail=False, methods=['get'], url_path='my-requests')
    def my_requests(self, request):
        qs = self.get_queryset().filter(requester=request.user)
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = BriefRequestListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        return Response({'success': True, 'data': BriefRequestListSerializer(
            qs, many=True, context={'request': request}
        ).data})

    @extend_schema(tags=['Brief Connect'], summary='Requests I have applied to')
    @action(detail=False, methods=['get'], url_path='my-applications')
    def my_applications(self, request):
        app_ids = BriefApplication.objects.filter(
            applicant=request.user, is_deleted=False
        ).values_list('brief_request_id', flat=True)
        qs = self.get_queryset().filter(id__in=app_ids)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = BriefRequestListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        return Response({'success': True, 'data': BriefRequestListSerializer(
            qs, many=True, context={'request': request}
        ).data})

    @extend_schema(tags=['Brief Connect'], summary='Apply to a brief request')
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        brief_request = self.get_object()
        if not _is_lawyer(request.user):
            return Response(
                {'success': False, 'message': 'Only lawyers can apply to brief requests.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = BriefApplicationCreateSerializer(
            data=request.data,
            context={'request': request, 'brief_request': brief_request},
        )
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        brief_request.update_application_count()

        from apps.brief_connect.tasks import notify_new_application
        _try_dispatch(notify_new_application, str(application.id))

        return Response(
            {'success': True, 'data': BriefApplicationSerializer(application, context={'request': request}).data},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(tags=['Brief Connect'], summary='Withdraw my application')
    @action(detail=True, methods=['post'], url_path='withdraw-application')
    def withdraw_application(self, request, pk=None):
        brief_request = self.get_object()
        try:
            application = brief_request.applications.get(applicant=request.user, is_deleted=False)
        except BriefApplication.DoesNotExist:
            return Response(
                {'success': False, 'message': 'You have not applied to this request.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if application.status != 'pending':
            return Response(
                {'success': False, 'message': 'Only pending applications can be withdrawn.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.status = 'withdrawn'
        application.save(update_fields=['status', 'updated_at'])
        brief_request.update_application_count()
        return Response({'success': True, 'message': 'Application withdrawn.'})

    @extend_schema(tags=['Brief Connect'], summary='Accept an application')
    @action(detail=True, methods=['post'], url_path='accept-application')
    def accept_application(self, request, pk=None):
        brief_request = self.get_object()
        if brief_request.requester != request.user:
            return Response(
                {'success': False, 'message': 'Only the requester can accept applications.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        application_id = request.data.get('application_id')
        if not application_id:
            return Response(
                {'success': False, 'message': 'application_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            application = brief_request.applications.get(id=application_id, is_deleted=False)
        except BriefApplication.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Application not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if application.status != 'pending':
            return Response(
                {'success': False, 'message': 'Only pending applications can be accepted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Accept the selected application, reject all others
        application.status = 'accepted'
        application.save(update_fields=['status', 'updated_at'])
        brief_request.applications.filter(
            is_deleted=False
        ).exclude(id=application.id).update(status='rejected')

        # Create the engagement
        agreed_fee = application.proposed_fee or brief_request.offered_fee
        engagement = BriefEngagement.objects.create(
            brief_request=brief_request,
            holding_lawyer=application.applicant,
            requester=brief_request.requester,
            agreed_fee=agreed_fee,
        )

        brief_request.status = 'accepted'
        brief_request.save(update_fields=['status', 'updated_at'])
        brief_request.update_application_count()

        from apps.brief_connect.tasks import notify_application_accepted, notify_application_rejected
        _try_dispatch(notify_application_accepted, str(application.id))
        rejected_ids = list(
            brief_request.applications.filter(
                status='rejected', is_deleted=False
            ).exclude(id=application.id).values_list('id', flat=True)
        )
        for rid in rejected_ids:
            _try_dispatch(notify_application_rejected, str(rid))

        return Response({
            'success': True,
            'message': 'Application accepted. Engagement created.',
            'data': BriefEngagementSerializer(engagement, context={'request': request}).data,
        })

    @extend_schema(tags=['Brief Connect'], summary='Reject an application')
    @action(detail=True, methods=['post'], url_path='reject-application')
    def reject_application(self, request, pk=None):
        brief_request = self.get_object()
        if brief_request.requester != request.user:
            return Response(
                {'success': False, 'message': 'Only the requester can reject applications.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        application_id = request.data.get('application_id')
        try:
            application = brief_request.applications.get(id=application_id, is_deleted=False)
        except BriefApplication.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Application not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if application.status != 'pending':
            return Response(
                {'success': False, 'message': 'Only pending applications can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.status = 'rejected'
        application.save(update_fields=['status', 'updated_at'])
        brief_request.update_application_count()

        from apps.brief_connect.tasks import notify_application_rejected
        _try_dispatch(notify_application_rejected, str(application.id))

        return Response({'success': True, 'message': 'Application rejected.'})


@extend_schema_view(
    list=extend_schema(tags=['Brief Connect'], summary='List my engagements'),
    retrieve=extend_schema(tags=['Brief Connect'], summary='Get engagement detail'),
)
class BriefEngagementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Engagement endpoints. Lawyers can view their own engagements and mark outcomes.
    """
    serializer_class = BriefEngagementSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        return BriefEngagement.objects.filter(
            Q(holding_lawyer=user) | Q(requester=user)
        ).select_related('brief_request', 'brief_request__court', 'holding_lawyer', 'requester')

    @extend_schema(tags=['Brief Connect'], summary='Mark engagement as completed')
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        engagement = self.get_object()
        if engagement.holding_lawyer != request.user:
            return Response(
                {'success': False, 'message': 'Only the holding lawyer can mark completion.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if engagement.status not in ('confirmed', 'in_progress'):
            return Response(
                {'success': False, 'message': 'Engagement is not in a completable state.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        engagement.status = 'completed'
        engagement.outcome_notes = request.data.get('outcome_notes', '')
        engagement.completed_at = timezone.now()
        engagement.save(update_fields=['status', 'outcome_notes', 'completed_at', 'updated_at'])

        engagement.brief_request.status = 'completed'
        engagement.brief_request.save(update_fields=['status', 'updated_at'])

        from apps.brief_connect.tasks import notify_engagement_completed
        _try_dispatch(notify_engagement_completed, str(engagement.id))

        return Response({
            'success': True,
            'message': 'Engagement marked as completed.',
            'data': BriefEngagementSerializer(engagement, context={'request': request}).data,
        })

    @extend_schema(tags=['Brief Connect'], summary='Mark engagement as in progress')
    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        engagement = self.get_object()
        if engagement.holding_lawyer != request.user:
            return Response(
                {'success': False, 'message': 'Only the holding lawyer can update this.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if engagement.status != 'confirmed':
            return Response(
                {'success': False, 'message': 'Engagement must be confirmed before starting.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        engagement.status = 'in_progress'
        engagement.save(update_fields=['status', 'updated_at'])
        return Response({
            'success': True,
            'data': BriefEngagementSerializer(engagement, context={'request': request}).data,
        })

    @extend_schema(tags=['Brief Connect'], summary='Raise a dispute on engagement')
    @action(detail=True, methods=['post'])
    def dispute(self, request, pk=None):
        engagement = self.get_object()
        if request.user not in (engagement.holding_lawyer, engagement.requester):
            return Response(
                {'success': False, 'message': 'Not your engagement.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if engagement.status not in ('confirmed', 'in_progress', 'completed'):
            return Response(
                {'success': False, 'message': 'Cannot dispute at this stage.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        engagement.status = 'disputed'
        engagement.save(update_fields=['status', 'updated_at'])
        return Response({'success': True, 'message': 'Dispute raised. Support will follow up.'})


@extend_schema_view(
    list=extend_schema(tags=['Brief Connect'], summary='List reviews for a lawyer'),
    create=extend_schema(tags=['Brief Connect'], summary='Submit a review'),
)
class BriefReviewViewSet(viewsets.ModelViewSet):
    """
    Review endpoints. Requesters can review the holding lawyer after a completed engagement.
    """
    serializer_class = BriefReviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        reviewee_id = self.request.query_params.get('lawyer_id')
        qs = BriefReview.objects.select_related('reviewer', 'reviewee')
        if reviewee_id:
            qs = qs.filter(reviewee_id=reviewee_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(
            {'success': True, 'data': BriefReviewSerializer(review, context={'request': request}).data},
            status=status.HTTP_201_CREATED,
        )

    def get_permissions(self):
        if self.action == 'list':
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        return Response(
            {'success': False, 'message': 'Reviews cannot be edited.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'success': False, 'message': 'Reviews cannot be deleted.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
