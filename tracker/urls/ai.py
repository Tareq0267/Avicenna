from django.urls import path
from tracker import views

urlpatterns = [
    path('ai/', views.ai_food_log, name='ai_food_log'),
    path('ai/parse/', views.ai_parse_food, name='ai_parse_food'),
    path('ai/save/', views.ai_save_food, name='ai_save_food'),
    path('ai/quota/', views.ai_quota_status, name='ai_quota_status'),
]
