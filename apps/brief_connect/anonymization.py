"""
Identity-visibility rules for Brief Connect.

Requesters and applicants are anonymous to everyone except themselves until
a BriefEngagement links them together — at that point both parties may see
each other's real identity.
"""
from .models import BriefEngagement


def is_connected(viewer, owner, brief_request):
    """True if `viewer` may see `owner`'s real identity on `brief_request`."""
    if not viewer or not getattr(viewer, 'is_authenticated', False):
        return False
    if viewer == owner:
        return True
    try:
        engagement = brief_request.engagement
    except BriefEngagement.DoesNotExist:
        return False
    parties = (engagement.requester, engagement.holding_lawyer)
    return viewer in parties and owner in parties
