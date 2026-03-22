from django.urls import path
from tracker import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/partner/', views.partner_dashboard, name='partner_dashboard'),
    path('', views.dashboard, name='dashboard-root'),
    path('import-json/', views.import_json, name='import_json'),
    path('guide/', views.guide, name='guide'),

    # Update Log
    path('changelog/', views.update_log, name='update_log'),

    # Settings
    path('settings/', views.settings_page, name='settings'),
    path('settings/update-username/', views.update_username, name='update_username'),
]
