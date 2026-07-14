"""
Server-side enforcement so policy consent can't be bypassed by calling the
API directly. Raise inside a view/action before performing the guarded
operation; the frontend catches `code: "policy_required"` and shows the
acceptance modal.
"""
from rest_framework import status
from rest_framework.exceptions import APIException

from .models import PolicyDocument, PolicyAcceptance


def has_accepted_latest(user, checkpoint):
    policy = PolicyDocument.current(checkpoint)
    if policy is None:
        return True
    return PolicyAcceptance.objects.filter(user=user, policy=policy).exists()


class PolicyRequiredError(APIException):
    """
    Matches the `CynosureException` convention in apps.common.exceptions —
    a plain string `detail` renders cleanly through the shared
    custom_exception_handler as {success: False, error: {code, message}}.
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You must accept the current policy for this action before continuing.'
    default_code = 'policy_required'

    def __init__(self, checkpoint):
        self.checkpoint = checkpoint
        super().__init__()


def require_policy_accepted(user, checkpoint):
    if not has_accepted_latest(user, checkpoint):
        raise PolicyRequiredError(checkpoint)
