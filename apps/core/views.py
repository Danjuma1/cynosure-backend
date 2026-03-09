"""
Core app - Health checks and system utilities.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


def health_check(request):
    """Basic health check endpoint."""
    return JsonResponse({'status': 'healthy', 'service': 'cynosure'})


def detailed_health_check(request):
    """Detailed health check with service status."""
    health = {
        'status': 'healthy',
        'services': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['services']['database'] = 'healthy'
    except Exception as e:
        health['services']['database'] = f'unhealthy: {str(e)}'
        health['status'] = 'degraded'
    
    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['services']['cache'] = 'healthy'
        else:
            health['services']['cache'] = 'unhealthy: cache read failed'
            health['status'] = 'degraded'
    except Exception as e:
        health['services']['cache'] = f'unhealthy: {str(e)}'
        health['status'] = 'degraded'
    
    return JsonResponse(health)


class SystemInfoView(APIView):
    """System information endpoint."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        from django.conf import settings
        
        return Response({
            'name': 'Cynosure Legal Platform',
            'version': '1.0.0',
            'environment': settings.DEBUG and 'development' or 'production',
            'api_version': 'v1',
        })
