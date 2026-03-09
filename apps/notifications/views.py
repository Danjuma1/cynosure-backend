"""
Views for notifications endpoints.
"""
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.common.pagination import NotificationCursorPagination, StandardResultsSetPagination
from .models import Notification, NotificationPreference, WebPushSubscription
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationPreferenceSerializer,
    WebPushSubscriptionSerializer,
    MarkReadSerializer,
    NotificationCountSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=['Notifications'], summary='List notifications'),
    retrieve=extend_schema(tags=['Notifications'], summary='Get notification details'),
)
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing notifications.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationCursorPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'is_read', 'is_archived', 'priority']
    
    def get_queryset(self):
        queryset = Notification.objects.filter(
            user=self.request.user,
            is_archived=False
        )
        
        # Filter by court
        court_id = self.request.query_params.get('court')
        if court_id:
            queryset = queryset.filter(court_id=court_id)
        
        # Filter by judge
        judge_id = self.request.query_params.get('judge')
        if judge_id:
            queryset = queryset.filter(judge_id=judge_id)
        
        # Filter by case
        case_id = self.request.query_params.get('case')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer
    
    @extend_schema(tags=['Notifications'], summary='Get notification counts')
    @action(detail=False, methods=['get'])
    def counts(self, request):
        """Get notification counts by type and status."""
        queryset = Notification.objects.filter(
            user=request.user,
            is_archived=False
        )
        
        total = queryset.count()
        unread = queryset.filter(is_read=False).count()
        
        by_type = dict(
            queryset.filter(is_read=False)
            .values('notification_type')
            .annotate(count=Count('id'))
            .values_list('notification_type', 'count')
        )
        
        return Response({
            'success': True,
            'data': {
                'total': total,
                'unread': unread,
                'by_type': by_type,
            }
        })
    
    @extend_schema(tags=['Notifications'], summary='Mark notifications as read')
    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Mark notifications as read."""
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        queryset = Notification.objects.filter(
            user=request.user,
            is_read=False
        )
        
        if serializer.validated_data.get('mark_all'):
            updated = queryset.update(is_read=True, read_at=timezone.now())
        else:
            notification_ids = serializer.validated_data.get('notification_ids', [])
            updated = queryset.filter(id__in=notification_ids).update(
                is_read=True, read_at=timezone.now()
            )
        
        return Response({
            'success': True,
            'message': f'Marked {updated} notifications as read.',
        })
    
    @extend_schema(tags=['Notifications'], summary='Mark single notification as read')
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark a single notification as read."""
        notification = self.get_object()
        notification.mark_read()
        
        return Response({
            'success': True,
            'message': 'Notification marked as read.',
        })
    
    @extend_schema(tags=['Notifications'], summary='Archive notifications')
    @action(detail=False, methods=['post'])
    def archive(self, request):
        """Archive notifications."""
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        queryset = Notification.objects.filter(
            user=request.user,
            is_archived=False
        )
        
        if serializer.validated_data.get('mark_all'):
            # Archive all read notifications
            updated = queryset.filter(is_read=True).update(
                is_archived=True, archived_at=timezone.now()
            )
        else:
            notification_ids = serializer.validated_data.get('notification_ids', [])
            updated = queryset.filter(id__in=notification_ids).update(
                is_archived=True, archived_at=timezone.now()
            )
        
        return Response({
            'success': True,
            'message': f'Archived {updated} notifications.',
        })
    
    @extend_schema(tags=['Notifications'], summary='Get archived notifications')
    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get archived notifications."""
        queryset = Notification.objects.filter(
            user=request.user,
            is_archived=True
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = NotificationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = NotificationListSerializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})
    
    @extend_schema(tags=['Notifications'], summary='Get unread notifications')
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications."""
        queryset = Notification.objects.filter(
            user=request.user,
            is_read=False,
            is_archived=False
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = NotificationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = NotificationListSerializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})


@extend_schema_view(
    retrieve=extend_schema(tags=['Notifications'], summary='Get notification preferences'),
    update=extend_schema(tags=['Notifications'], summary='Update notification preferences'),
    partial_update=extend_schema(tags=['Notifications'], summary='Partially update preferences'),
)
class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification preferences.
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'patch']
    
    def get_object(self):
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference
    
    def list(self, request, *args, **kwargs):
        """Get preferences (redirect to retrieve)."""
        return self.retrieve(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data,
        })
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Preferences updated successfully.',
            'data': serializer.data,
        })


@extend_schema_view(
    list=extend_schema(tags=['Notifications'], summary='List web push subscriptions'),
    create=extend_schema(tags=['Notifications'], summary='Subscribe to web push'),
    destroy=extend_schema(tags=['Notifications'], summary='Unsubscribe from web push'),
)
class WebPushSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing web push subscriptions.
    """
    serializer_class = WebPushSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        return WebPushSubscription.objects.filter(
            user=self.request.user,
            is_active=True
        )
    
    def perform_create(self, serializer):
        # Deactivate existing subscription with same endpoint
        WebPushSubscription.objects.filter(
            user=self.request.user,
            endpoint=serializer.validated_data['endpoint']
        ).update(is_active=False)
        
        serializer.save(user=self.request.user)
    
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])
