"""
Celery tasks for Brief Connect notifications.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='apps.brief_connect.tasks.notify_brief_request_posted')
def notify_brief_request_posted(brief_request_id: str):
    """Notify lawyers in the same court area about a new brief request."""
    from apps.brief_connect.models import BriefRequest
    from apps.notifications.services import create_notification
    from apps.authentication.models import User

    try:
        req = BriefRequest.objects.select_related('requester', 'court').get(id=brief_request_id)

        # Notify all active lawyers except the requester
        lawyers = User.objects.filter(
            user_type__in=['lawyer', 'firm_admin'],
            is_active=True,
        ).exclude(id=req.requester_id)

        for lawyer in lawyers:
            create_notification(
                user=lawyer,
                notification_type='brief_connect_new_request',
                title=f'New Brief Request — {req.court.name}',
                message=(
                    f'{req.requester.full_name} is looking for someone to '
                    f'{req.get_brief_type_display().lower()} on {req.hearing_date}.'
                ),
                priority='normal',
                action_url=f'/brief-connect/requests/{req.id}',
                data={'brief_request_id': str(req.id)},
                send_immediately=False,
            )

        logger.info(f"Brief request {brief_request_id} notification sent to {lawyers.count()} lawyers")
        return {'status': 'success', 'notified': lawyers.count()}
    except Exception as e:
        logger.error(f"Failed to notify for brief request {brief_request_id}: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.brief_connect.tasks.notify_new_application')
def notify_new_application(application_id: str):
    """Notify the requester that someone applied to their brief request."""
    from apps.brief_connect.models import BriefApplication
    from apps.notifications.services import create_notification

    try:
        app = BriefApplication.objects.select_related(
            'applicant', 'brief_request', 'brief_request__court', 'brief_request__requester'
        ).get(id=application_id)

        req = app.brief_request
        create_notification(
            user=req.requester,
            notification_type='brief_connect_application',
            title='New Application on Your Brief Request',
            message=(
                f'{app.applicant.full_name} has applied to hold your brief at '
                f'{req.court.name} on {req.hearing_date}.'
            ),
            priority='high',
            action_url=f'/brief-connect/requests/{req.id}',
            data={'brief_request_id': str(req.id), 'application_id': str(app.id)},
        )

        logger.info(f"Notified requester {req.requester_id} of application {application_id}")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Failed to notify for application {application_id}: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.brief_connect.tasks.notify_application_accepted')
def notify_application_accepted(application_id: str):
    """Notify the applicant that their application was accepted."""
    from apps.brief_connect.models import BriefApplication
    from apps.notifications.services import create_notification

    try:
        app = BriefApplication.objects.select_related(
            'applicant', 'brief_request', 'brief_request__court', 'brief_request__requester'
        ).get(id=application_id)

        req = app.brief_request
        create_notification(
            user=app.applicant,
            notification_type='brief_connect_accepted',
            title='Your Application Was Accepted',
            message=(
                f'{req.requester.full_name} has accepted your application to hold brief at '
                f'{req.court.name} on {req.hearing_date}. Contact them to confirm details.'
            ),
            priority='urgent',
            action_url=f'/brief-connect/my-briefs',
            data={'brief_request_id': str(req.id), 'application_id': str(app.id)},
        )

        logger.info(f"Notified applicant {app.applicant_id} of acceptance")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Failed to notify for acceptance {application_id}: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.brief_connect.tasks.notify_application_rejected')
def notify_application_rejected(application_id: str):
    """Notify the applicant that their application was not selected."""
    from apps.brief_connect.models import BriefApplication
    from apps.notifications.services import create_notification

    try:
        app = BriefApplication.objects.select_related(
            'applicant', 'brief_request', 'brief_request__court'
        ).get(id=application_id)

        req = app.brief_request
        create_notification(
            user=app.applicant,
            notification_type='brief_connect_rejected',
            title='Application Not Selected',
            message=(
                f'Your application to hold brief at {req.court.name} on {req.hearing_date} '
                f'was not selected. Keep an eye out for other opportunities.'
            ),
            priority='normal',
            action_url='/brief-connect',
            data={'brief_request_id': str(req.id)},
        )

        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Failed to notify rejection {application_id}: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.brief_connect.tasks.notify_engagement_completed')
def notify_engagement_completed(engagement_id: str):
    """Notify the requester that the holding lawyer has marked the engagement complete."""
    from apps.brief_connect.models import BriefEngagement
    from apps.notifications.services import create_notification

    try:
        eng = BriefEngagement.objects.select_related(
            'requester', 'holding_lawyer', 'brief_request', 'brief_request__court'
        ).get(id=engagement_id)

        create_notification(
            user=eng.requester,
            notification_type='brief_connect_completed',
            title='Brief Engagement Completed',
            message=(
                f'{eng.holding_lawyer.full_name} has marked your brief engagement at '
                f'{eng.brief_request.court.name} as completed. Please leave a review.'
            ),
            priority='normal',
            action_url='/brief-connect/my-briefs',
            data={'engagement_id': str(eng.id)},
        )

        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Failed to notify engagement completion {engagement_id}: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.brief_connect.tasks.expire_overdue_requests')
def expire_overdue_requests():
    """Expire open brief requests whose hearing date has passed."""
    from django.utils.timezone import now
    from apps.brief_connect.models import BriefRequest

    today = now().date()
    expired = BriefRequest.objects.filter(
        status='open',
        hearing_date__lt=today,
        is_deleted=False,
    ).update(status='expired')

    logger.info(f"Expired {expired} overdue brief requests")
    return {'status': 'success', 'expired': expired}
