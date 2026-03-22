from django.urls import path, include

app_name = 'tracker'

urlpatterns = []

# Include all module URL files
from .core import urlpatterns as core_urls
from .diet import urlpatterns as diet_urls
from .exercise import urlpatterns as exercise_urls
from .ai import urlpatterns as ai_urls
from .routines import urlpatterns as routine_urls

urlpatterns += core_urls
urlpatterns += diet_urls
urlpatterns += exercise_urls
urlpatterns += ai_urls
urlpatterns += routine_urls
