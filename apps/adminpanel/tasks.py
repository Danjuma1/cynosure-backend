"""Admin panel Celery tasks."""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.adminpanel.tasks.generate_weekly_analytics')
def generate_weekly_analytics():
    """Generate weekly analytics report."""
    from datetime import timedelta
    from apps.courts.models import Court
    from apps.judges.models import Judge
    from apps.cases.models import Case
    from apps.cause_lists.models import CauseList
    from apps.authentication.models import User
    from apps.notifications.models import Notification
    from apps.common.models import SystemConfiguration
    
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        report = {
            'period': {'start': str(start_date), 'end': str(end_date)},
            'new_users': User.objects.filter(date_joined__date__gte=start_date).count(),
            'new_cases': Case.objects.filter(created_at__date__gte=start_date).count(),
            'cause_lists_published': CauseList.objects.filter(
                published_at__date__gte=start_date
            ).count(),
            'notifications_sent': Notification.objects.filter(
                created_at__date__gte=start_date
            ).count(),
            'active_courts': Court.objects.filter(is_active=True).count(),
            'active_judges': Judge.objects.filter(status='active').count(),
            'generated_at': str(timezone.now()),
        }
        
        # Store report
        SystemConfiguration.objects.update_or_create(
            key='weekly_analytics_report',
            defaults={
                'value': report,
                'description': f'Weekly analytics report for {start_date} to {end_date}'
            }
        )
        
        logger.info(f"Weekly analytics generated: {report}")
        return {'status': 'success', 'report': report}
        
    except Exception as e:
        logger.error(f"Failed to generate weekly analytics: {e}")
        return {'status': 'error', 'message': str(e)}
