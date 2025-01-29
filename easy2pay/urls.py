from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponseRedirect
from django.conf import settings
from django.conf.urls.static import static

def redirect_to_login(request):
    # Check if the request path starts with '/admin/' to avoid redirecting admin requests
    if request.path.startswith('/admin/'):
        return None  # Do not redirect, allow the request to proceed
    return HttpResponseRedirect('/easy2pay/login/')  # Redirect to login for all other paths

urlpatterns = [
    path('admin/', admin.site.urls),
    path("easy2pay/", include("ourapp.urls")),
    path("", redirect_to_login),  # Redirect root URL to login page
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)