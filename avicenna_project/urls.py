

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from tracker.views import custom_logout
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tracker/', include('tracker.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
        path('accounts/logout/', custom_logout, name='logout'),
    path('', lambda request: redirect('tracker:dashboard')),
]
