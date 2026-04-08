from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views, logout as auth_logout
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def _logout_view(request):
    auth_logout(request)
    return redirect('/login/')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', _logout_view, name='logout'),
    path('', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
