from django.urls import path
from tracker import views

urlpatterns = [
    path('routines/', views.routine_tracker, name='routine_tracker'),
    path('routines/add/', views.add_routine, name='add_routine'),
    path('routines/edit/<int:routine_id>/', views.edit_routine, name='edit_routine'),
    path('routines/delete/<int:routine_id>/', views.delete_routine, name='delete_routine'),
    path('routines/toggle/<int:routine_id>/', views.toggle_completion, name='toggle_completion'),
    path('routines/preset/', views.add_preset, name='add_preset'),
    path('routines/reorder/', views.reorder_routines, name='reorder_routines'),
]
