import logging
import uuid

from django.conf import settings
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.brief_connect.models import BriefEngagement
from apps.policies.enforcement import require_policy_accepted
from . import paystack, services
from .fees import calculate_fee
from .models import LawyerBankAccount, EscrowAccount, PaystackTransaction, PlatformFeeSetting
from .serializers import LawyerBankAccountSerializer, EscrowAccountSerializer

logger = logging.getLogger(__name__)


class FeeConfigView(APIView):
    """GET /payments/fee-config/ — current commission percentage for client-side fee previews."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Payments'], summary='Get current platform fee percentage')
    def get(self, request):
        return Response({'success': True, 'data': {'percentage': str(PlatformFeeSetting.current())}})


class BankAccountViewSet(viewsets.ModelViewSet):
    """A lawyer's payout bank accounts. Verified against Paystack before saving."""
    serializer_class = LawyerBankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LawyerBankAccount.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        bank_code = request.data.get('bank_code')
        account_number = request.data.get('account_number')
        if not bank_code or not account_number:
            return Response(
                {'success': False, 'message': 'bank_code and account_number are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            resolved = paystack.resolve_account_number(account_number, bank_code)
        except paystack.PaystackError as exc:
            return Response(
                {'success': False, 'message': f'Could not verify this account: {exc}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        LawyerBankAccount.objects.filter(user=request.user).update(is_default=False)
        account = LawyerBankAccount.objects.create(
            user=request.user,
            bank_code=bank_code,
            bank_name=request.data.get('bank_name', ''),
            account_number=account_number,
            account_name=resolved.get('account_name', ''),
            verified=True,
            is_default=True,
        )
        return Response(
            {'success': True, 'data': LawyerBankAccountSerializer(account).data},
            status=status.HTTP_201_CREATED,
        )


class BanksListView(APIView):
    """GET /payments/banks/ — list of Nigerian banks for the bank-account picker."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Payments'], summary='List Nigerian banks (Paystack)')
    def get(self, request):
        try:
            banks = paystack.list_banks()
        except paystack.PaystackError as exc:
            return Response({'success': False, 'message': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'success': True, 'data': banks})


class EngagementEscrowView(GenericAPIView):
    """GET /brief-connect/engagements/{engagement_id}/escrow/"""
    permission_classes = [IsAuthenticated]
    serializer_class = EscrowAccountSerializer

    def get(self, request, engagement_id):
        try:
            engagement = BriefEngagement.objects.get(id=engagement_id)
        except (BriefEngagement.DoesNotExist, ValueError):
            return Response({'success': False, 'message': 'Engagement not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user not in (engagement.requester, engagement.holding_lawyer):
            return Response({'success': False, 'message': 'Engagement not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            escrow = engagement.escrow
        except EscrowAccount.DoesNotExist:
            return Response({'success': False, 'message': 'No escrow has been set up for this engagement.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': EscrowAccountSerializer(escrow).data})


class EscrowInitializeView(APIView):
    """POST /payments/escrow/{engagement_id}/initialize/ — start funding via Paystack."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Payments'], summary='Initialize escrow funding')
    def post(self, request, engagement_id):
        try:
            engagement = BriefEngagement.objects.get(id=engagement_id)
        except (BriefEngagement.DoesNotExist, ValueError):
            return Response({'success': False, 'message': 'Engagement not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user != engagement.requester:
            return Response({'success': False, 'message': 'Only the requester can fund escrow.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            escrow = engagement.escrow
        except EscrowAccount.DoesNotExist:
            return Response({'success': False, 'message': 'No escrow has been set up for this engagement.'}, status=status.HTTP_404_NOT_FOUND)
        if escrow.status != 'pending':
            return Response({'success': False, 'message': f'Escrow is already {escrow.status}.'}, status=status.HTTP_400_BAD_REQUEST)

        require_policy_accepted(request.user, 'escrow')

        reference = f'bc-escrow-{escrow.id}-{uuid.uuid4().hex[:8]}'
        amount_kobo = int(escrow.total_charged * 100)
        try:
            result = paystack.initialize_transaction(
                email=request.user.email,
                amount_kobo=amount_kobo,
                reference=reference,
                callback_url=request.data.get('callback_url'),
                metadata={'engagement_id': str(engagement.id), 'escrow_id': str(escrow.id)},
            )
        except paystack.PaystackError as exc:
            return Response({'success': False, 'message': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        PaystackTransaction.objects.create(
            escrow=escrow, reference=reference, amount_kobo=amount_kobo, status='pending',
        )
        return Response({'success': True, 'data': {
            'authorization_url': result.get('authorization_url'),
            'access_code': result.get('access_code'),
            'reference': reference,
        }})


class EscrowVerifyView(APIView):
    """POST /payments/escrow/{engagement_id}/verify/ — redirect-callback fallback verification."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Payments'], summary='Verify an escrow funding transaction')
    def post(self, request, engagement_id):
        reference = request.data.get('reference')
        if not reference:
            return Response({'success': False, 'message': 'reference is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            transaction = PaystackTransaction.objects.select_related('escrow__engagement').get(
                reference=reference, escrow__engagement_id=engagement_id,
            )
        except PaystackTransaction.DoesNotExist:
            return Response({'success': False, 'message': 'Transaction not found.'}, status=status.HTTP_404_NOT_FOUND)

        engagement = transaction.escrow.engagement
        if request.user not in (engagement.requester, engagement.holding_lawyer):
            return Response({'success': False, 'message': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        _verify_and_fund(transaction)
        return Response({'success': True, 'data': EscrowAccountSerializer(transaction.escrow).data})


def _verify_and_fund(transaction):
    """Shared by the manual verify endpoint and the Paystack webhook."""
    if transaction.status == 'success':
        return
    try:
        result = paystack.verify_transaction(transaction.reference)
    except paystack.PaystackError as exc:
        logger.warning('Brief Connect: could not verify transaction %s: %s', transaction.reference, exc)
        return
    transaction.raw_response = result
    if result.get('status') == 'success':
        transaction.status = 'success'
        transaction.paid_at = timezone.now()
        transaction.save(update_fields=['status', 'paid_at', 'raw_response'])

        escrow = transaction.escrow
        if escrow.status == 'pending':
            escrow.status = 'funded'
            escrow.funded_at = timezone.now()
            escrow.save(update_fields=['status', 'funded_at', 'updated_at'])
    else:
        transaction.status = result.get('status', 'failed')
        transaction.save(update_fields=['status', 'raw_response'])


class PaystackWebhookView(APIView):
    """POST /payments/webhooks/paystack/ — Paystack server-to-server events."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get('x-paystack-signature', '')
        if not paystack.verify_webhook_signature(request.body, signature):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        event = request.data.get('event')
        data = request.data.get('data', {})

        if event == 'charge.success':
            reference = data.get('reference')
            transaction = PaystackTransaction.objects.filter(reference=reference).first()
            if transaction:
                _verify_and_fund(transaction)
        elif event in ('transfer.success', 'transfer.failed', 'transfer.reversed'):
            transfer_code = data.get('transfer_code')
            from .models import Payout
            payout = Payout.objects.filter(paystack_transfer_code=transfer_code).first()
            if payout:
                payout.status = data.get('status', payout.status)
                payout.raw_response = data
                payout.save(update_fields=['status', 'raw_response'])

        return Response({'success': True})
