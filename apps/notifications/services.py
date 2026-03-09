"""
Notification delivery services.
"""
import json
import logging
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_email_notification(notification):
    """
    Send email notification.
    """
    try:
        user = notification.user
        
        # Render email template
        context = {
            'user': user,
            'notification': notification,
            'title': notification.title,
            'message': notification.message,
            'action_url': notification.action_url,
        }
        
        html_message = render_to_string(
            f'emails/notifications/{notification.notification_type}.html',
            context
        )
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=notification.title,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email sent to {user.email} for notification {notification.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        raise


def send_push_notification(notification):
    """
    Send push notification via Firebase Cloud Messaging.
    """
    from apps.authentication.models import DeviceToken
    
    try:
        user = notification.user
        
        # Get user's device tokens
        tokens = DeviceToken.objects.filter(
            user=user,
            is_active=True
        ).values_list('token', 'platform')
        
        if not tokens:
            logger.debug(f"No device tokens for user {user.id}")
            return False
        
        fcm_key = settings.FCM_SERVER_KEY
        if not fcm_key:
            logger.warning("FCM_SERVER_KEY not configured")
            return False
        
        headers = {
            'Authorization': f'key={fcm_key}',
            'Content-Type': 'application/json',
        }
        
        for token, platform in tokens:
            payload = {
                'to': token,
                'notification': {
                    'title': notification.title,
                    'body': notification.message,
                    'click_action': notification.action_url,
                },
                'data': {
                    'notification_id': str(notification.id),
                    'type': notification.notification_type,
                    **notification.data,
                },
            }
            
            response = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"FCM error: {response.text}")
                # Deactivate invalid token
                if 'InvalidRegistration' in response.text or 'NotRegistered' in response.text:
                    DeviceToken.objects.filter(token=token).update(is_active=False)
        
        logger.info(f"Push notification sent for notification {notification.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        raise


def send_webpush_notification(notification):
    """
    Send web push notification.
    """
    from pywebpush import webpush, WebPushException
    from .models import WebPushSubscription
    
    try:
        user = notification.user
        
        subscriptions = WebPushSubscription.objects.filter(
            user=user,
            is_active=True
        )
        
        if not subscriptions:
            return False
        
        vapid_settings = settings.WEBPUSH_SETTINGS
        if not vapid_settings.get('VAPID_PRIVATE_KEY'):
            logger.warning("VAPID keys not configured")
            return False
        
        payload = json.dumps({
            'title': notification.title,
            'body': notification.message,
            'icon': '/static/icons/notification.png',
            'url': notification.action_url,
            'data': {
                'notification_id': str(notification.id),
                'type': notification.notification_type,
            },
        })
        
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub.endpoint,
                        'keys': {
                            'p256dh': sub.p256dh,
                            'auth': sub.auth,
                        },
                    },
                    data=payload,
                    vapid_private_key=vapid_settings['VAPID_PRIVATE_KEY'],
                    vapid_claims={
                        'sub': f"mailto:{vapid_settings['VAPID_ADMIN_EMAIL']}",
                    },
                )
            except WebPushException as e:
                logger.error(f"WebPush error: {e}")
                if e.response and e.response.status_code in [404, 410]:
                    sub.is_active = False
                    sub.save(update_fields=['is_active'])
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send web push notification: {e}")
        raise


def send_sms_notification(notification):
    """
    Send SMS notification (placeholder for SMS gateway integration).
    """
    # TODO: Integrate with SMS gateway (e.g., Twilio, Africa's Talking)
    logger.info(f"SMS notification would be sent for {notification.id}")
    return False


def create_notification(
    user,
    notification_type,
    title,
    message,
    priority='normal',
    court_id=None,
    judge_id=None,
    case_id=None,
    cause_list_id=None,
    action_url='',
    data=None,
    send_immediately=True
):
    """
    Create and optionally send a notification.
    """
    from .models import Notification, NotificationPreference
    
    # Check user preferences
    try:
        pref = NotificationPreference.objects.get(user=user)
        type_pref = getattr(pref, notification_type.replace('-', '_'), True)
        if not type_pref:
            logger.debug(f"User {user.id} has disabled {notification_type} notifications")
            return None
    except NotificationPreference.DoesNotExist:
        pass
    
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        court_id=court_id,
        judge_id=judge_id,
        case_id=case_id,
        cause_list_id=cause_list_id,
        action_url=action_url,
        data=data or {},
    )
    
    if send_immediately:
        from .tasks import process_pending_notifications
        process_pending_notifications.delay()
    
    return notification
