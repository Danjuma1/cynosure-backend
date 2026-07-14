import logging

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.common.permissions import IsRegistryOrAdmin
from apps.payments import services as payment_services
from apps.payments.models import EscrowAccount
from .models import Dispute, DisputeEvidence
from .serializers import DisputeSerializer, DisputeEvidenceSerializer

logger = logging.getLogger(__name__)


def _is_admin(user):
    return user.is_authenticated and (user.user_type in ('registry_staff', 'super_admin') or user.is_superuser)


@extend_schema_view(
    list=extend_schema(tags=['Disputes'], summary='List disputes (own, or all for admins)'),
    retrieve=extend_schema(tags=['Disputes'], summary='Get dispute detail'),
)
class DisputeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DisputeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Dispute.objects.select_related(
            'engagement', 'engagement__requester', 'engagement__holding_lawyer', 'raised_by', 'resolved_by',
        ).prefetch_related('evidence')
        if _is_admin(user):
            return qs
        return qs.filter(Q(engagement__requester=user) | Q(engagement__holding_lawyer=user))

    @extend_schema(tags=['Disputes'], summary='Add evidence to a dispute')
    @action(detail=True, methods=['post'], url_path='add-evidence')
    def add_evidence(self, request, pk=None):
        dispute = self.get_object()
        if dispute.status not in ('open', 'under_review'):
            return Response(
                {'success': False, 'message': 'This dispute is already resolved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        parties = (dispute.engagement.requester, dispute.engagement.holding_lawyer)
        if request.user not in parties and not _is_admin(request.user):
            return Response({'success': False, 'message': 'Not your dispute.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = DisputeEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence = serializer.save(dispute=dispute, submitted_by=request.user)
        if dispute.status == 'open':
            dispute.status = 'under_review'
            dispute.save(update_fields=['status', 'updated_at'])
        return Response(
            {'success': True, 'data': DisputeEvidenceSerializer(evidence).data},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(tags=['Disputes'], summary='Resolve a dispute (admin only)')
    @action(detail=True, methods=['post'], permission_classes=[IsRegistryOrAdmin])
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        if dispute.status not in ('open', 'under_review'):
            return Response(
                {'success': False, 'message': 'This dispute is already resolved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resolution = request.data.get('resolution')
        if resolution not in ('release', 'refund', 'split'):
            return Response(
                {'success': False, 'message': 'resolution must be one of: release, refund, split.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            escrow = dispute.engagement.escrow
        except EscrowAccount.DoesNotExist:
            return Response(
                {'success': False, 'message': 'No escrow exists for this engagement.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if escrow.status != 'disputed':
            return Response(
                {'success': False, 'message': f'Escrow is {escrow.status}, not under dispute — nothing to resolve.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if resolution == 'release':
                payment_services.release_escrow_full(escrow)
                dispute.status = 'resolved_release'
            elif resolution == 'refund':
                payment_services.refund_escrow_full(escrow)
                dispute.status = 'resolved_refund'
            else:
                lawyer_amount = request.data.get('split_lawyer_amount')
                refund_amount = request.data.get('split_requester_refund_amount')
                if lawyer_amount is None or refund_amount is None:
                    return Response(
                        {'success': False, 'message': 'split_lawyer_amount and split_requester_refund_amount are required for a split.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                payment_services.split_escrow(escrow, lawyer_amount, refund_amount)
                dispute.status = 'resolved_split'
                dispute.split_lawyer_amount = lawyer_amount
                dispute.split_requester_refund_amount = refund_amount
        except ValueError as exc:
            return Response({'success': False, 'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception('Dispute resolution failed for %s: %s', dispute.id, exc)
            return Response({'success': False, 'message': 'Resolution failed. Please try again.'}, status=status.HTTP_502_BAD_GATEWAY)

        dispute.resolution_notes = request.data.get('notes', '')
        dispute.resolved_by = request.user
        dispute.resolved_at = timezone.now()
        dispute.save(update_fields=[
            'status', 'resolution_notes', 'resolved_by', 'resolved_at',
            'split_lawyer_amount', 'split_requester_refund_amount', 'updated_at',
        ])

        engagement = dispute.engagement
        engagement.status = 'completed' if resolution != 'refund' else 'cancelled'
        engagement.save(update_fields=['status', 'updated_at'])

        return Response({'success': True, 'data': DisputeSerializer(dispute).data})
