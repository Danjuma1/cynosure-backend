"""
Custom middleware for Cynosure.
"""
import json
import logging
import time
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to log user actions for audit purposes.
    """
    EXCLUDED_PATHS = ['/health/', '/api/schema/', '/static/', '/media/']
    LOGGED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_response(self, request, response):
        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return response
        
        # Only log certain methods
        if request.method not in self.LOGGED_METHODS:
            return response
        
        # Only log authenticated requests
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        
        # Skip if response indicates an error
        if response.status_code >= 400:
            return response
        
        try:
            from apps.common.models import AuditLog
            
            # Determine action based on method
            action_map = {
                'POST': 'CREATE',
                'PUT': 'UPDATE',
                'PATCH': 'UPDATE',
                'DELETE': 'DELETE',
            }
            
            # Try to get the model name from the URL
            path_parts = request.path.strip('/').split('/')
            model_name = path_parts[2] if len(path_parts) > 2 else 'unknown'
            object_id = path_parts[3] if len(path_parts) > 3 else ''
            
            # Get changes (for POST/PUT/PATCH)
            changes = {}
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    if hasattr(request, 'data'):
                        # Sanitize sensitive fields
                        data = dict(request.data)
                        for key in ['password', 'token', 'secret']:
                            if key in data:
                                data[key] = '***'
                        changes = data
                except Exception:
                    pass
            
            AuditLog.objects.create(
                user=request.user,
                action=action_map.get(request.method, 'UPDATE'),
                model_name=model_name,
                object_id=object_id,
                changes=changes,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                endpoint=request.path[:500],
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware using Redis.
    """
    DEFAULT_RATE_LIMIT = 100  # requests per minute
    WINDOW_SIZE = 60  # seconds
    
    RATE_LIMITS = {
        '/api/v1/auth/login/': 10,
        '/api/v1/auth/signup/': 5,
        '/api/v1/auth/password-reset/': 5,
    }
    
    def process_request(self, request):
        # Get client identifier
        client_id = self.get_client_identifier(request)
        
        # Get rate limit for this endpoint
        rate_limit = self.RATE_LIMITS.get(request.path, self.DEFAULT_RATE_LIMIT)
        
        # Check rate limit
        cache_key = f'ratelimit:{client_id}:{request.path}'
        
        try:
            current_count = cache.get(cache_key, 0)
            
            if current_count >= rate_limit:
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'detail': f'Maximum {rate_limit} requests per minute allowed.'
                    },
                    status=429
                )
            
            # Increment counter
            cache.set(cache_key, current_count + 1, self.WINDOW_SIZE)
        except Exception as e:
            logger.warning(f"Rate limiting failed: {e}")
        
        return None
    
    def get_client_identifier(self, request):
        """Get a unique identifier for the client."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f'user:{request.user.id}'
        
        # Use IP address for anonymous users
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return f'ip:{ip}'


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom JWT authentication middleware for Django Channels WebSockets.
    """
    
    async def __call__(self, scope, receive, send):
        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = dict(
            param.split('=') for param in query_string.split('&') if '=' in param
        )
        
        token = query_params.get('token')
        
        if token:
            try:
                # Validate token
                access_token = AccessToken(token)
                user_id = access_token.get('user_id')
                
                # Get user
                user = await self.get_user(user_id)
                scope['user'] = user
            except (InvalidToken, TokenError) as e:
                logger.warning(f"WebSocket authentication failed: {e}")
                scope['user'] = None
        else:
            scope['user'] = None
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database."""
        from apps.authentication.models import User
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None


class RequestTimingMiddleware(MiddlewareMixin):
    """
    Middleware to measure and log request processing time.
    """
    SLOW_REQUEST_THRESHOLD = 1.0  # seconds
    
    def process_request(self, request):
        request._start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            # Add timing header
            response['X-Request-Duration'] = f'{duration:.3f}s'
            
            # Log slow requests
            if duration > self.SLOW_REQUEST_THRESHOLD:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.3f}s"
                )
        
        return response
