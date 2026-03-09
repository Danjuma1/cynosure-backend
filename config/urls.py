"""
Cynosure URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# API URL patterns (versioned)
api_v1_patterns = [
    path('auth/', include('apps.authentication.urls')),
    path('courts/', include('apps.courts.urls')),
    path('judges/', include('apps.judges.urls')),
    path('cases/', include('apps.cases.urls')),
    path('cause-lists/', include('apps.cause_lists.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('search/', include('apps.search.urls')),
    path('repository/', include('apps.repository.urls')),
    path('firms/', include('apps.firms.urls')),
    path('efiling/', include('apps.efiling.urls')),
    path('admin-panel/', include('apps.adminpanel.urls')),
]

urlpatterns = [
    # Django Admin
    path('django-admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include((api_v1_patterns, 'api_v1'), namespace='v1')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health check
    path('health/', include('apps.core.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Admin site customization
admin.site.site_header = 'Cynosure Administration'
admin.site.site_title = 'Cynosure Admin'
admin.site.index_title = 'Welcome to Cynosure Admin Portal'
