import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.common.pagination import StandardResultsSetPagination
from apps.brief_connect.models import BriefEngagement
from .models import Message
from .serializers import MessageSerializer

logger = logging.getLogger(__name__)


class EngagementMessageListCreateView(GenericAPIView):
    """
    GET/POST /brief-connect/engagements/{engagement_id}/messages/
    Chat history + send, restricted to the engagement's two parties.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_engagement(self, request, engagement_id):
        try:
            engagement = BriefEngagement.objects.select_related('requester', 'holding_lawyer').get(id=engagement_id)
        except (BriefEngagement.DoesNotExist, ValueError):
            return None
        if request.user not in (engagement.requester, engagement.holding_lawyer):
            return None
        return engagement

    @extend_schema(tags=['Brief Connect Chat'], summary='List messages for an engagement')
    def get(self, request, engagement_id):
        engagement = self._get_engagement(request, engagement_id)
        if not engagement:
            return Response(
                {'success': False, 'message': 'Engagement not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = engagement.messages.select_related('sender')
        page = self.paginate_queryset(qs)
        serializer = MessageSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @extend_schema(tags=['Brief Connect Chat'], summary='Send a message on an engagement')
    def post(self, request, engagement_id):
        engagement = self._get_engagement(request, engagement_id)
        if not engagement:
            return Response(
                {'success': False, 'message': 'Engagement not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MessageSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(engagement=engagement, sender=request.user)

        data = MessageSerializer(message, context={'request': request}).data
        channel_layer = get_channel_layer()
        try:
            async_to_sync(channel_layer.group_send)(f'brief_chat_{engagement.id}', {
                'type': 'chat_message',
                'message': data,
            })
        except Exception as exc:
            logger.warning('Brief Connect chat: could not broadcast message %s: %s', message.id, exc)

        return Response({'success': True, 'data': data}, status=status.HTTP_201_CREATED)
