"""
Celery tasks for courts app.
"""
from celery import shared_task
from django.core.cache import cache
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)


@shared_task(name='apps.courts.tasks.refresh_court_cache')
def refresh_court_cache():
    """
    Refresh cached court data.
    Runs periodically to keep cache warm.
    """
    from .models import Court
    
    try:
        # Refresh statistics cache
        courts = Court.objects.filter(is_deleted=False)
        
        stats = {
            'total_courts': courts.count(),
            'active_courts': courts.filter(is_active=True).count(),
            'courts_by_type': dict(
                courts.values('court_type')
                .annotate(count=Count('id'))
                .values_list('court_type', 'count')
            ),
            'courts_by_state': dict(
                courts.values('state')
                .annotate(count=Count('id'))
                .values_list('state', 'count')
            ),
            'total_judges': sum(c.total_judges for c in courts),
            'total_divisions': sum(c.total_divisions for c in courts),
        }
        
        cache.set('courts:statistics', stats, timeout=3600)
        
        # Clear list caches
        cache.delete_pattern('courts:list:*')
        
        logger.info("Court cache refreshed successfully")
        return {'status': 'success', 'stats': stats}
        
    except Exception as e:
        logger.error(f"Failed to refresh court cache: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.courts.tasks.update_court_statistics')
def update_court_statistics(court_id=None):
    """
    Update statistics for a specific court or all courts.
    """
    from .models import Court, Division
    from apps.judges.models import Judge
    
    try:
        if court_id:
            courts = Court.objects.filter(id=court_id)
        else:
            courts = Court.objects.filter(is_deleted=False)
        
        for court in courts:
            # Update judge count
            judge_count = Judge.objects.filter(
                court=court,
                is_deleted=False,
                is_active=True
            ).count()
            
            # Update division count
            division_count = Division.objects.filter(
                court=court,
                is_deleted=False,
                is_active=True
            ).count()
            
            court.total_judges = judge_count
            court.total_divisions = division_count
            court.save(update_fields=['total_judges', 'total_divisions', 'updated_at'])
        
        logger.info(f"Updated statistics for {courts.count()} courts")
        return {'status': 'success', 'updated': courts.count()}
        
    except Exception as e:
        logger.error(f"Failed to update court statistics: {e}")
        return {'status': 'error', 'message': str(e)}
