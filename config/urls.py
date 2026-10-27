"""
URL configuration for SpeakPro AI project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseForbidden, HttpResponse

def block_public_tts(request, path=""):
    return HttpResponseForbidden("Public access to TTS audio is disabled.")

def favicon_view(request):
    return HttpResponse(status=204)

urlpatterns = [
    path('favicon.ico', favicon_view, name='favicon'),
    path('admin/', admin.site.urls),
    path('media/tts/<path:path>', block_public_tts, name='block_public_tts'),
    path('', include('app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
