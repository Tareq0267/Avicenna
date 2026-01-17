from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/partner/', views.partner_dashboard, name='partner_dashboard'),
    path('', views.dashboard, name='dashboard-root'),
    path('import-json/', views.import_json, name='import_json'),
    path('add-weight/', views.add_weight, name='add_weight'),
    path('daily-recap/<str:date_str>/', views.daily_recap, name='daily_recap'),
    path('daily-recap/<str:date_str>/user/<int:user_id>/', views.daily_recap, name='daily_recap_user'),
    path('guide/', views.guide, name='guide'),

    # Delete entry URLs
    path('delete-dietary/<int:entry_id>/', views.delete_dietary_entry, name='delete_dietary_entry'),
    path('delete-exercise/<int:entry_id>/', views.delete_exercise_entry, name='delete_exercise_entry'),
    path('delete-weight/<int:entry_id>/', views.delete_weight_entry, name='delete_weight_entry'),
]
