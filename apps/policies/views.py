from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import PolicyDocument, PolicyAcceptance
from .serializers import PolicyDocumentSerializer
from .enforcement import has_accepted_latest


class PendingPolicyView(GenericAPIView):
    """
    GET /policies/pending/?checkpoint=posting
    Returns the active policy document if the current user hasn't accepted
    its latest version yet, else 204 No Content.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PolicyDocumentSerializer

    @extend_schema(
        tags=['Policies'],
        parameters=[OpenApiParameter('checkpoint', str, description='One of: posting, applying, escrow, completion')],
        summary='Get the pending (unaccepted) policy for a checkpoint',
    )
    def get(self, request):
        checkpoint = request.query_params.get('checkpoint')
        valid_checkpoints = dict(PolicyDocument.CHECKPOINT_CHOICES)
        if checkpoint not in valid_checkpoints:
            return Response(
                {'success': False, 'message': 'A valid checkpoint query param is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if has_accepted_latest(request.user, checkpoint):
            return Response(status=status.HTTP_204_NO_CONTENT)
        policy = PolicyDocument.current(checkpoint)
        return Response({'success': True, 'data': PolicyDocumentSerializer(policy).data})


class AcceptPolicyView(GenericAPIView):
    """POST /policies/accept/ {policy_id} — records acceptance for the current user."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Policies'], summary='Accept a policy document')
    def post(self, request):
        policy_id = request.data.get('policy_id')
        try:
            policy = PolicyDocument.objects.get(id=policy_id, is_active=True)
        except (PolicyDocument.DoesNotExist, ValueError, TypeError):
            return Response(
                {'success': False, 'message': 'Policy not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        PolicyAcceptance.objects.get_or_create(user=request.user, policy=policy)
        return Response({'success': True, 'message': 'Policy accepted.'})
