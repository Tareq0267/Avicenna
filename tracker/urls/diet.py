from django.urls import path
from tracker import views

urlpatterns = [
    path('add-weight/', views.add_weight, name='add_weight'),
    path('daily-recap/<str:date_str>/', views.daily_recap, name='daily_recap'),
    path('daily-recap/<str:date_str>/user/<int:user_id>/', views.daily_recap, name='daily_recap_user'),

    # Calorie Goal Setup
    path('calorie-setup/', views.calorie_setup, name='calorie_setup'),
    path('calorie-settings/', views.update_calorie_settings, name='update_calorie_settings'),

    # Delete entries
    path('delete-dietary/<int:entry_id>/', views.delete_dietary_entry, name='delete_dietary_entry'),
    path('delete-weight/<int:entry_id>/', views.delete_weight_entry, name='delete_weight_entry'),
]
