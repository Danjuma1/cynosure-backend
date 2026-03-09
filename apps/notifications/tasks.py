"""
Celery tasks for notifications.
"""
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


@shared_task(name='apps.notifications.tasks.notify_new_cause_list')
def notify_new_cause_list(cause_list_id: str):
    """Send notifications for a new cause list."""
    from apps.cause_lists.models import CauseList
    from apps.authentication.models import UserFollowing
    from .models import Notification, NotificationBatch
    
    try:
        cause_list = CauseList.objects.select_related('court', 'judge').get(id=cause_list_id)
        
        followers = set()
        court_followers = UserFollowing.objects.filter(
            follow_type='court',
            object_id=cause_list.court_id,
            notifications_enabled=True
        ).values_list('user_id', flat=True)
        followers.update(court_followers)
        
        if cause_list.judge:
            judge_followers = UserFollowing.objects.filter(
                follow_type='judge',
                object_id=cause_list.judge_id,
                notifications_enabled=True
            ).values_list('user_id', flat=True)
            followers.update(judge_followers)
        
        batch = NotificationBatch.objects.create(
            notification_type='cause_list_new',
            title=f'New Cause List: {cause_list.court.name}',
            message=f'Cause list published for {cause_list.date}',
            target_court_id=cause_list.court_id,
            target_judge_id=cause_list.judge_id if cause_list.judge else None,
            total_recipients=len(followers),
            data={'cause_list_id': str(cause_list_id), 'date': str(cause_list.date)}
        )
        
        notifications = []
        for user_id in followers:
            notifications.append(Notification(
                user_id=user_id,
                notification_type='cause_list_new',
                title=f'New Cause List: {cause_list.court.name}',
                message=f'Cause list for {cause_list.judge.formal_name if cause_list.judge else "Court"} on {cause_list.date}',
                priority='normal',
                court_id=cause_list.court_id,
                judge_id=cause_list.judge_id if cause_list.judge else None,
                cause_list_id=cause_list.id,
                action_url=f'/cause-lists/{cause_list.id}',
                data={'batch_id': str(batch.id)}
            ))
        
        if notifications:
            Notification.objects.bulk_create(notifications, batch_size=100)
        
        batch.sent_count = len(notifications)
        batch.status = 'completed'
        batch.processed_at = timezone.now()
        batch.save()
        
        send_websocket_notification.delay(str(cause_list_id), 'cause_list_created', {
            'court_id': str(cause_list.court_id),
            'judge_id': str(cause_list.judge_id) if cause_list.judge else None,
            'date': str(cause_list.date),
        })
        
        logger.info(f"Sent {len(notifications)} notifications for cause list {cause_list_id}")
        return {'status': 'success', 'sent': len(notifications)}
    except Exception as e:
        logger.error(f"Failed to send cause list notifications: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.notifications.tasks.notify_cause_list_change')
def notify_cause_list_change(cause_list_id: str, changes: dict):
    """Send notifications for cause list changes."""
    from apps.cause_lists.models import CauseList
    from apps.authentication.models import UserFollowing
    from .models import Notification
    
    try:
        cause_list = CauseList.objects.select_related('court', 'judge').get(id=cause_list_id)
        
        if 'status' in changes:
            notification_type = 'cause_list_status'
            title = f'Status Changed: {cause_list.court.name}'
            message = f'Status changed to {changes["status"]["new"]}'
        elif 'start_time' in changes or 'end_time' in changes:
            notification_type = 'time_change'
            title = f'Time Changed: {cause_list.court.name}'
            message = f'Time updated for cause list on {cause_list.date}'
        elif 'courtroom' in changes:
            notification_type = 'courtroom_change'
            title = f'Courtroom Changed: {cause_list.court.name}'
            message = f'Courtroom changed for {cause_list.date}'
        else:
            notification_type = 'cause_list_update'
            title = f'Cause List Updated: {cause_list.court.name}'
            message = f'Cause list for {cause_list.date} has been updated'
        
        followers = set()
        court_followers = UserFollowing.objects.filter(
            follow_type='court', object_id=cause_list.court_id, notifications_enabled=True
        ).values_list('user_id', flat=True)
        followers.update(court_followers)
        
        if cause_list.judge:
            judge_followers = UserFollowing.objects.filter(
                follow_type='judge', object_id=cause_list.judge_id, notifications_enabled=True
            ).values_list('user_id', flat=True)
            followers.update(judge_followers)
        
        notifications = []
        for user_id in followers:
            notifications.append(Notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                priority='high' if notification_type == 'cause_list_status' else 'normal',
                court_id=cause_list.court_id,
                judge_id=cause_list.judge_id if cause_list.judge else None,
                cause_list_id=cause_list.id,
                action_url=f'/cause-lists/{cause_list.id}',
                data={'changes': changes}
            ))
        
        if notifications:
            Notification.objects.bulk_create(notifications, batch_size=100)
        
        logger.info(f"Sent {len(notifications)} change notifications for cause list {cause_list_id}")
        return {'status': 'success', 'sent': len(notifications)}
    except Exception as e:
        logger.error(f"Failed to send cause list change notifications: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.notifications.tasks.notify_cause_list_status_change')
def notify_cause_list_status_change(cause_list_id: str, old_status: str, new_status: str):
    """Send notifications for cause list status change."""
    changes = {'status': {'old': old_status, 'new': new_status}}
    return notify_cause_list_change(cause_list_id, changes)


@shared_task(name='apps.notifications.tasks.notify_judge_status_change')
def notify_judge_status_change(judge_id: str, new_status: str):
    """Send notifications for judge status change."""
    from apps.judges.models import Judge
    from apps.authentication.models import UserFollowing
    from .models import Notification
    
    try:
        judge = Judge.objects.select_related('court').get(id=judge_id)
        followers = UserFollowing.objects.filter(
            follow_type='judge', object_id=judge_id, notifications_enabled=True
        ).values_list('user_id', flat=True)
        
        status_display = dict(Judge.STATUS_CHOICES).get(new_status, new_status)
        
        notifications = []
        for user_id in followers:
            notifications.append(Notification(
                user_id=user_id,
                notification_type='judge_status',
                title=f'Judge Status Update: {judge.formal_name}',
                message=f'{judge.formal_name} is now {status_display}',
                priority='high' if new_status in ['not_sitting', 'on_leave'] else 'normal',
                court_id=judge.court_id,
                judge_id=judge.id,
                action_url=f'/judges/{judge.id}',
            ))
        
        if notifications:
            Notification.objects.bulk_create(notifications, batch_size=100)
        
        logger.info(f"Sent {len(notifications)} status notifications for judge {judge_id}")
        return {'status': 'success', 'sent': len(notifications)}
    except Exception as e:
        logger.error(f"Failed to send judge status notifications: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.notifications.tasks.send_case_reminders')
def send_case_reminders():
    """Send reminders for cases scheduled today."""
    from datetime import date
    from apps.authentication.models import UserFollowing
    from apps.cause_lists.models import CauseListEntry
    from .models import Notification
    
    try:
        today = date.today()
        entries = CauseListEntry.objects.filter(
            cause_list__date=today,
            cause_list__status__in=['published', 'sitting'],
            is_deleted=False
        ).select_related('cause_list', 'cause_list__court', 'cause_list__judge', 'case')
        
        notifications = []
        for entry in entries:
            if entry.case:
                case_followers = UserFollowing.objects.filter(
                    follow_type='case', object_id=entry.case_id, notifications_enabled=True
                ).values_list('user_id', flat=True)
                
                for user_id in case_followers:
                    notifications.append(Notification(
                        user_id=user_id,
                        notification_type='case_on_docket',
                        title=f'Your Case is Today: {entry.case_number}',
                        message=f'Case {entry.case_number} is scheduled for today at {entry.cause_list.court.name}',
                        priority='high',
                        court_id=entry.cause_list.court_id,
                        judge_id=entry.cause_list.judge_id if entry.cause_list.judge else None,
                        case_id=entry.case_id,
                        cause_list_id=entry.cause_list_id,
                        action_url=f'/cases/{entry.case_id}',
                        data={'case_number': entry.case_number, 'time': str(entry.scheduled_time) if entry.scheduled_time else None}
                    ))
        
        if notifications:
            Notification.objects.bulk_create(notifications, batch_size=100)
        
        logger.info(f"Sent {len(notifications)} case reminders for {today}")
        return {'status': 'success', 'sent': len(notifications)}
    except Exception as e:
        logger.error(f"Failed to send case reminders: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.notifications.tasks.generate_daily_summaries')
def generate_daily_summaries():
    """Generate and send daily summary emails."""
    from .models import Notification, NotificationPreference
    from apps.common.utils import send_notification_email
    from datetime import timedelta
    
    try:
        yesterday = timezone.now() - timedelta(days=1)
        preferences = NotificationPreference.objects.filter(
            daily_digest=True, email_enabled=True
        ).select_related('user')
        
        sent_count = 0
        for pref in preferences:
            notifications = Notification.objects.filter(
                user=pref.user, created_at__date=yesterday.date()
            ).order_by('-created_at')
            
            if notifications.exists():
                by_type = {}
                for notif in notifications:
                    notif_type = notif.get_notification_type_display()
                    if notif_type not in by_type:
                        by_type[notif_type] = []
                    by_type[notif_type].append(notif)
                
                send_notification_email(
                    to_email=pref.user.email,
                    subject=f'Your Daily Cynosure Summary - {yesterday.date()}',
                    template_name='daily_digest',
                    context={
                        'user': pref.user,
                        'date': yesterday.date(),
                        'notifications_by_type': by_type,
                        'total_count': notifications.count(),
                    }
                )
                sent_count += 1
        
        logger.info(f"Sent {sent_count} daily summary emails")
        return {'status': 'success', 'sent': sent_count}
    except Exception as e:
        logger.error(f"Failed to generate daily summaries: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.notifications.tasks.process_pending_notifications')
def process_pending_notifications():
    """Process pending notification deliveries."""
    from .models import Notification
    from .services import send_push_notification, send_email_notification
    
    try:
        cutoff = timezone.now() - timezone.timedelta(hours=1)
        
        email_pending = Notification.objects.filter(
            email_sent=False, created_at__gte=cutoff
        ).select_related('user')[:100]
        
        email_sent = 0
        for notif in email_pending:
            if notif.user.email_notifications:
                try:
                    send_email_notification(notif)
                    notif.email_sent = True
                    notif.email_sent_at = timezone.now()
                    notif.save(update_fields=['email_sent', 'email_sent_at'])
                    email_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send email for notification {notif.id}: {e}")
        
        push_pending = Notification.objects.filter(
            push_sent=False, created_at__gte=cutoff
        ).select_related('user')[:100]
        
        push_sent = 0
        for notif in push_pending:
            if notif.user.push_notifications:
                try:
                    send_push_notification(notif)
                    notif.push_sent = True
                    notif.push_sent_at = timezone.now()
                    notif.save(update_fields=['push_sent', 'push_sent_at'])
                    push_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send push for notification {notif.id}: {e}")
        
        logger.info(f"Processed notifications - Email: {email_sent}, Push: {push_sent}")
        return {'status': 'success', 'email': email_sent, 'push': push_sent}
    except Exception as e:
        logger.error(f"Failed to process pending notifications: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.notifications.tasks.archive_old_notifications')
def archive_old_notifications():
    """Archive old read notifications."""
    from datetime import timedelta
    from .models import Notification
    
    try:
        cutoff = timezone.now() - timedelta(days=30)
        updated = Notification.objects.filter(
            is_read=True, is_archived=False, created_at__lt=cutoff
        ).update(is_archived=True, archived_at=timezone.now())
        
        logger.info(f"Archived {updated} old notifications")
        return {'status': 'success', 'archived': updated}
    except Exception as e:
        logger.error(f"Failed to archive old notifications: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.notifications.tasks.send_websocket_notification')
def send_websocket_notification(object_id: str, event_type: str, data: dict):
    """Send real-time WebSocket notification."""
    try:
        channel_layer = get_channel_layer()
        
        groups = [
            'cause_list_all',
            f'cause_list_{object_id}',
        ]
        
        if data.get('court_id'):
            groups.append(f'cause_list_court_{data["court_id"]}')
        if data.get('judge_id'):
            groups.append(f'cause_list_judge_{data["judge_id"]}')
        if data.get('date'):
            groups.append(f'cause_list_date_{data["date"]}')
        
        message = {'type': event_type, 'data': data, 'object_id': object_id}
        
        for group in groups:
            async_to_sync(channel_layer.group_send)(group, {
                'type': event_type.replace('-', '_'),
                **message
            })
        
        logger.info(f"Sent WebSocket notification to {len(groups)} groups")
        return {'status': 'success', 'groups': len(groups)}
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {e}")
        return {'status': 'error', 'message': str(e)}
