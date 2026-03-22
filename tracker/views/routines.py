import json
from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from tracker.models import Routine, CompletionRecord
from tracker.routine_presets import get_presets_by_group, add_preset_for_user, add_preset_group_for_user
from tracker.views.core import _get_routine_streak


@login_required
def routine_tracker(request):
    """Main routine tracker page with today's checklist and gamification."""
    today = timezone.now().date()
    user = request.user

    # Get user's active routines scheduled for today
    all_routines = Routine.objects.filter(user=user, is_active=True)
    todays_routines = [r for r in all_routines if r.is_scheduled_for(today)]

    # Sort by scheduled time, then by order
    def sort_key(r):
        t = r.get_scheduled_time()
        return (t if t else '99:99', r.order)
    todays_routines.sort(key=sort_key)

    # Get today's completions
    completed_ids = set(
        CompletionRecord.objects.filter(user=user, date=today)
        .values_list('routine_id', flat=True)
    )

    # Build checklist data
    checklist = []
    for routine in todays_routines:
        checklist.append({
            'routine': routine,
            'completed': routine.id in completed_ids,
            'streak': _get_routine_streak(routine, user, today),
        })

    total_today = len(todays_routines)
    done_today = len([c for c in checklist if c['completed']])

    # 7-day history
    week_history = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        count = CompletionRecord.objects.filter(user=user, date=d).count()
        scheduled = len([r for r in all_routines if r.is_scheduled_for(d)])
        week_history.append({
            'date': d,
            'day_name': d.strftime('%a'),
            'completed': count,
            'total': scheduled,
            'is_today': d == today,
        })

    # Presets
    preset_groups = get_presets_by_group()

    # Mark already-added presets
    existing_preset_keys = set(
        Routine.objects.filter(user=user, is_active=True, preset_key__gt='')
        .values_list('preset_key', flat=True)
    )

    icon_choices = [
        'bi-check-circle', 'bi-star', 'bi-heart', 'bi-lightning-charge',
        'bi-book', 'bi-moon-stars', 'bi-sun', 'bi-droplet', 'bi-cup-straw',
        'bi-bicycle', 'bi-person-walking', 'bi-pencil', 'bi-music-note',
        'bi-palette', 'bi-code-slash', 'bi-camera', 'bi-chat-dots',
        'bi-clock', 'bi-trophy',
    ]

    context = {
        'checklist': checklist,
        'total_today': total_today,
        'done_today': done_today,
        'progress_percent': round(done_today / total_today * 100) if total_today > 0 else 0,
        'week_history': week_history,
        'preset_groups': preset_groups,
        'existing_preset_keys': existing_preset_keys,
        'all_routines': all_routines,
        'icon_choices': icon_choices,
    }
    return render(request, 'tracker/routine_tracker.html', context)


@login_required
@require_POST
def toggle_completion(request, routine_id):
    """Toggle a routine's completion for today."""
    try:
        routine = Routine.objects.get(id=routine_id, user=request.user, is_active=True)
    except Routine.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Routine not found'}, status=404)

    today = timezone.now().date()

    try:
        # Already completed - undo it
        record = CompletionRecord.objects.get(routine=routine, date=today)
        record.delete()
        completed = False
    except CompletionRecord.DoesNotExist:
        # Mark as completed
        CompletionRecord.objects.create(
            routine=routine,
            user=request.user,
            date=today,
        )
        completed = True

    # Check if all routines are done for confetti burst
    all_routines = Routine.objects.filter(user=request.user, is_active=True)
    todays_routines = [r for r in all_routines if r.is_scheduled_for(today)]
    completed_count = CompletionRecord.objects.filter(user=request.user, date=today).count()
    all_done = completed_count >= len(todays_routines) and len(todays_routines) > 0

    streak = _get_routine_streak(routine, request.user, today) if completed else 0

    return JsonResponse({
        'success': True,
        'completed': completed,
        'trigger_confetti': completed,
        'all_done': all_done,
        'done_today': completed_count,
        'total_today': len(todays_routines),
        'streak': streak,
    })


@login_required
@require_POST
def add_routine(request):
    """Create a custom routine."""
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Name is required'}, status=400)

    schedule_type = request.POST.get('schedule_type', 'daily')
    schedule_config = {}

    time_val = request.POST.get('time', '').strip()
    if time_val:
        schedule_config['time'] = time_val

    if schedule_type == 'weekly':
        days = request.POST.getlist('days')
        schedule_config['days'] = [int(d) for d in days if d.isdigit()]
    elif schedule_type == 'monthly':
        dates = request.POST.getlist('dates')
        schedule_config['dates'] = [int(d) for d in dates if d.isdigit()]

    routine = Routine.objects.create(
        user=request.user,
        name=name,
        description=request.POST.get('description', '').strip(),
        schedule_type=schedule_type,
        schedule_config=schedule_config,
        icon=request.POST.get('icon', 'bi-check-circle'),
        color=request.POST.get('color', '#818cf8'),
    )

    return JsonResponse({
        'success': True,
        'routine_id': routine.id,
        'message': f'"{routine.name}" added!',
    })


@login_required
@require_POST
def edit_routine(request, routine_id):
    """Update a routine."""
    try:
        routine = Routine.objects.get(id=routine_id, user=request.user)
    except Routine.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Routine not found'}, status=404)

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Name is required'}, status=400)

    routine.name = name
    routine.description = request.POST.get('description', '').strip()
    routine.schedule_type = request.POST.get('schedule_type', routine.schedule_type)
    routine.icon = request.POST.get('icon', routine.icon)
    routine.color = request.POST.get('color', routine.color)

    schedule_config = {}
    time_val = request.POST.get('time', '').strip()
    if time_val:
        schedule_config['time'] = time_val
    if routine.schedule_type == 'weekly':
        days = request.POST.getlist('days')
        schedule_config['days'] = [int(d) for d in days if d.isdigit()]
    elif routine.schedule_type == 'monthly':
        dates = request.POST.getlist('dates')
        schedule_config['dates'] = [int(d) for d in dates if d.isdigit()]
    routine.schedule_config = schedule_config

    routine.save()
    return JsonResponse({'success': True, 'message': f'"{routine.name}" updated!'})


@login_required
@require_POST
def delete_routine(request, routine_id):
    """Deactivate a routine (soft delete to preserve history)."""
    try:
        routine = Routine.objects.get(id=routine_id, user=request.user)
    except Routine.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Routine not found'}, status=404)

    routine.is_active = False
    routine.save()
    return JsonResponse({'success': True, 'message': f'"{routine.name}" removed.'})


@login_required
@require_POST
def add_preset(request):
    """Add a preset routine or an entire group."""
    preset_key = request.POST.get('preset_key', '').strip()
    group = request.POST.get('group', '').strip()

    if group:
        created = add_preset_group_for_user(request.user, group)
        if created:
            return JsonResponse({
                'success': True,
                'message': f'Added {len(created)} routines!',
                'count': len(created),
            })
        return JsonResponse({'success': True, 'message': 'All presets in this group already added.', 'count': 0})
    elif preset_key:
        routine = add_preset_for_user(request.user, preset_key)
        if routine:
            return JsonResponse({'success': True, 'message': f'"{routine.name}" added!'})
        return JsonResponse({'success': True, 'message': 'Preset already added.'})
    else:
        return JsonResponse({'success': False, 'error': 'No preset specified'}, status=400)


@login_required
@require_POST
def reorder_routines(request):
    """Update display order of routines."""
    try:
        order_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    for item in order_data:
        Routine.objects.filter(id=item['id'], user=request.user).update(order=item['order'])

    return JsonResponse({'success': True})
