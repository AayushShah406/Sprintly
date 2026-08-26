from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Core User Views
    path('', include('dashboard.urls', namespace='dashboard')),
    path('projects/', include('projects.urls', namespace='projects')),
    path('issues/', include('issues.urls', namespace='issues')),
    path('sprints/', include('sprints.urls', namespace='sprints')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('', include('accounts.urls', namespace='accounts')),
    
    # REST API endpoints
    path('api/auth/', include('accounts.urls')),
    path('api/projects/', include('projects.urls')),
    path('api/sprints/', include('sprints.urls')),
    path('api/issues/', include('issues.urls')),
    path('api/analytics/', include('analytics.urls', namespace='analytics')),
    path('api/notifications/', include('notifications.urls')),
    path('api/ai/', include('ai_assistant.urls', namespace='ai_assistant')),
]

handler404 = 'config.views.error_404'
handler403 = 'config.views.error_403'
handler500 = 'config.views.error_500'

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None)
