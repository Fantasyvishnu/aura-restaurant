from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Untouched Default Django Admin Panel
    path('admin/', admin.site.urls),
    # Restaurant App URLs (includes custom Admin Dashboard and Customer Portals)
    path('', include('main.urls')),
]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
