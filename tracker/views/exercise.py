from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from tracker.models import ExerciseEntry


@login_required
@require_POST
def delete_exercise_entry(request, entry_id):
    try:
        entry = ExerciseEntry.objects.get(id=entry_id, user=request.user)
    except ExerciseEntry.DoesNotExist:
        return HttpResponseForbidden()
    entry.delete()
    return redirect('tracker:dashboard')
