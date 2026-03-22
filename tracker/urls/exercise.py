from django.urls import path
from tracker import views

urlpatterns = [
    path('delete-exercise/<int:entry_id>/', views.delete_exercise_entry, name='delete_exercise_entry'),
]
