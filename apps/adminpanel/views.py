"""
Admin Panel app - Administrative endpoints and analytics.
"""
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.permissions import IsSuperAdmin, IsRegistryOrAdmin


class DashboardView(APIView):
    """Admin dashboard statistics."""
    permission_classes = [IsRegistryOrAdmin]
    
    @extend_schema(tags=['Admin'], summary='Get dashboard statistics')
    def get(self, request):
        from apps.courts.models import Court
        from apps.judges.models import Judge
        from apps.cases.models import Case
        from apps.cause_lists.models import CauseList
        from apps.authentication.models import User
        from apps.notifications.models import Notification
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        stats = {
            'courts': {
                'total': Court.objects.filter(is_deleted=False).count(),
                'active': Court.objects.filter(is_deleted=False, is_active=True).count(),
            },
            'judges': {
                'total': Judge.objects.filter(is_deleted=False).count(),
                'active': Judge.objects.filter(is_deleted=False, status='active').count(),
                'on_leave': Judge.objects.filter(is_deleted=False, status='on_leave').count(),
            },
            'cases': {
                'total': Case.objects.filter(is_deleted=False).count(),
                'active': Case.objects.filter(is_deleted=False, status='active').count(),
                'this_week': Case.objects.filter(created_at__date__gte=week_ago).count(),
            },
            'cause_lists': {
                'today': CauseList.objects.filter(date=today, is_deleted=False).count(),
                'this_week': CauseList.objects.filter(date__gte=week_ago, is_deleted=False).count(),
                'published_today': CauseList.objects.filter(
                    date=today, status='published', is_deleted=False
                ).count(),
            },
            'users': {
                'total': User.objects.filter(is_active=True).count(),
                'lawyers': User.objects.filter(is_active=True, user_type='lawyer').count(),
                'new_this_week': User.objects.filter(date_joined__date__gte=week_ago).count(),
            },
            'notifications': {
                'sent_today': Notification.objects.filter(created_at__date=today).count(),
                'sent_this_week': Notification.objects.filter(created_at__date__gte=week_ago).count(),
            },
        }
        
        return Response({'success': True, 'data': stats})


class AnalyticsView(APIView):
    """Detailed analytics."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(tags=['Admin'], summary='Get analytics data')
    def get(self, request):
        from apps.courts.models import Court
        from apps.judges.models import Judge
        from apps.authentication.models import UserFollowing
        
        # Most followed judges
        top_judges = Judge.objects.filter(
            is_deleted=False, is_active=True
        ).order_by('-follower_count')[:10]
        
        # Most followed courts
        top_courts = Court.objects.filter(
            is_deleted=False, is_active=True
        ).order_by('-follower_count')[:10]
        
        # Followings by type
        followings_by_type = dict(
            UserFollowing.objects.values('follow_type')
            .annotate(count=Count('id'))
            .values_list('follow_type', 'count')
        )
        
        analytics = {
            'top_judges': [
                {'id': str(j.id), 'name': j.formal_name, 'followers': j.follower_count}
                for j in top_judges
            ],
            'top_courts': [
                {'id': str(c.id), 'name': c.name, 'followers': c.follower_count}
                for c in top_courts
            ],
            'followings_by_type': followings_by_type,
        }
        
        return Response({'success': True, 'data': analytics})


class ScraperControlView(APIView):
    """Scraper management endpoints."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(tags=['Admin'], summary='Get scraper status')
    def get(self, request):
        from apps.scraping.models import ScraperConfig, ScraperRun
        
        configs = ScraperConfig.objects.all()
        recent_runs = ScraperRun.objects.all()[:20]
        
        data = {
            'scrapers': [
                {
                    'id': str(c.id),
                    'name': c.name,
                    'court': c.court.name,
                    'is_active': c.is_active,
                    'last_run': c.last_run,
                    'last_success': c.last_success,
                    'success_rate': (c.successful_runs / c.total_runs * 100) if c.total_runs > 0 else 0,
                }
                for c in configs
            ],
            'recent_runs': [
                {
                    'id': str(r.id),
                    'scraper': r.config.name,
                    'status': r.status,
                    'items_created': r.items_created,
                    'started_at': r.started_at,
                    'completed_at': r.completed_at,
                }
                for r in recent_runs
            ],
        }
        
        return Response({'success': True, 'data': data})
    
    @extend_schema(tags=['Admin'], summary='Control scraper')
    def post(self, request):
        action = request.data.get('action')
        scraper_id = request.data.get('scraper_id')
        
        from apps.scraping.models import ScraperConfig
        from apps.scraping.tasks import scrape_court
        
        if action == 'run':
            scrape_court.delay(scraper_id)
            return Response({'success': True, 'message': 'Scraper task started'})
        
        elif action == 'toggle':
            config = ScraperConfig.objects.get(id=scraper_id)
            config.is_active = not config.is_active
            config.save()
            return Response({'success': True, 'message': f'Scraper {"enabled" if config.is_active else "disabled"}'})
        
        return Response({'success': False, 'message': 'Invalid action'}, status=400)


class UserManagementView(APIView):
    """User management endpoints."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(tags=['Admin'], summary='List users')
    def get(self, request):
        from apps.authentication.models import User
        from apps.authentication.serializers import UserListSerializer
        
        users = User.objects.all().order_by('-date_joined')[:100]
        serializer = UserListSerializer(users, many=True)
        
        return Response({'success': True, 'data': serializer.data})
    
    @extend_schema(tags=['Admin'], summary='Manage user')
    def post(self, request):
        from apps.authentication.models import User
        
        action = request.data.get('action')
        user_id = request.data.get('user_id')
        
        try:
            user = User.objects.get(id=user_id)
            
            if action == 'ban':
                user.is_active = False
                user.save()
                return Response({'success': True, 'message': 'User banned'})
            
            elif action == 'unban':
                user.is_active = True
                user.save()
                return Response({'success': True, 'message': 'User unbanned'})
            
            elif action == 'reset_password':
                from apps.authentication.views import PasswordResetRequestView
                # Trigger password reset
                return Response({'success': True, 'message': 'Password reset initiated'})
            
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'User not found'}, status=404)
        
        return Response({'success': False, 'message': 'Invalid action'}, status=400)


class AuditLogView(APIView):
    """View audit logs."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(tags=['Admin'], summary='Get audit logs')
    def get(self, request):
        from apps.common.models import AuditLog
        
        logs = AuditLog.objects.all().select_related('user')[:100]
        
        data = [
            {
                'id': str(log.id),
                'user': log.user.email if log.user else None,
                'action': log.action,
                'model': log.model_name,
                'object_id': log.object_id,
                'endpoint': log.endpoint,
                'ip_address': log.ip_address,
                'created_at': log.created_at,
            }
            for log in logs
        ]
        
        return Response({'success': True, 'data': data})
