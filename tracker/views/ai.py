import json
from datetime import datetime

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from tracker.models import DietaryEntry, ExerciseEntry, Routine, CompletionRecord
from tracker.services.rate_limit import check_rate_limit, log_ai_usage, get_user_quota_info
from tracker.services.ai_service import AIFoodLogService
from tracker.services.calorie_calculator import get_calorie_status


@login_required
def ai_food_log(request):
    """Render the AI food logging page."""
    # Check if user has AI access enabled
    if not hasattr(request.user, 'profile') or not request.user.profile.ai_enabled:
        return render(request, 'tracker/ai_access_denied.html', status=403)
    return render(request, 'tracker/ai_food_log.html')


@require_POST
@login_required
def ai_parse_food(request):
    """Process text or image input through AI and return structured data."""
    # Check if user has AI access enabled
    if not hasattr(request.user, 'profile') or not request.user.profile.ai_enabled:
        return JsonResponse({'success': False, 'error': 'AI features not enabled for your account'}, status=403)

    # Apply rate limiting
    allowed, error_msg, remaining = check_rate_limit(request.user)

    if not allowed:
        return JsonResponse({
            'success': False,
            'error': error_msg,
            'rate_limit': True,
            'remaining': remaining
        }, status=429)

    request_type = 'image' if request.FILES.get('image') else 'text'

    try:
        # Get user's calorie context for personalized feedback
        user_context = None
        calorie_status = get_calorie_status(request.user)
        if calorie_status:
            user_context = {
                'goal': calorie_status['fitness_goal'],
                'daily_calorie_goal': calorie_status['daily_goal'],
                'calories_today': calorie_status['calories_consumed'],
                'calories_remaining': calorie_status['calories_remaining']
            }

        # Add routine context for coach feedback
        today = timezone.now().date()
        all_routines = Routine.objects.filter(user=request.user, is_active=True)
        todays_routines = [r for r in all_routines if r.is_scheduled_for(today)]
        completed_ids = set(
            CompletionRecord.objects.filter(user=request.user, date=today)
            .values_list('routine_id', flat=True)
        )
        if todays_routines:
            routine_context = {
                'total': len(todays_routines),
                'completed': len([r for r in todays_routines if r.id in completed_ids]),
                'items': [
                    {'name': r.name, 'done': r.id in completed_ids}
                    for r in todays_routines
                ]
            }
            if user_context is None:
                user_context = {}
            user_context['routines'] = routine_context

        service = AIFoodLogService(user_context=user_context)

        # Check if this is a text or image request
        text_input = request.POST.get('text', '').strip()
        image_file = request.FILES.get('image')

        if image_file:
            # Handle image input
            image_data = image_file.read()
            content_type = image_file.content_type
            context = request.POST.get('context', '').strip()

            # Validate file size (max 10MB)
            if len(image_data) > 10 * 1024 * 1024:
                log_ai_usage(request.user, request_type, success=False, error_message='Image too large')
                return JsonResponse({'success': False, 'error': 'Image too large (max 10MB)'})

            result = service.parse_image_input(image_data, content_type, context)
        elif text_input:
            # Handle text input
            result = service.parse_text_input(text_input)
        else:
            return JsonResponse({'success': False, 'error': 'No text or image provided'})

        # Log usage
        log_ai_usage(
            request.user,
            request_type,
            success=result.get('success', False),
            error_message=result.get('error', '') if not result.get('success') else ''
        )

        # Add remaining quota to response
        result['remaining'] = remaining

        return JsonResponse(result)

    except ValueError as e:
        # API key not configured
        log_ai_usage(request.user, request_type, success=False, error_message=str(e))
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        log_ai_usage(request.user, request_type, success=False, error_message=str(e))
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})


@require_POST
@login_required
def ai_save_food(request):
    """Save AI-parsed (and user-edited) food and exercise data."""
    # Check if user has AI access enabled
    if not hasattr(request.user, 'profile') or not request.user.profile.ai_enabled:
        return JsonResponse({'success': False, 'error': 'AI features not enabled for your account'}, status=403)

    try:
        raw_json = request.POST.get('json_data', '').strip()
        if not raw_json:
            return JsonResponse({'success': False, 'error': 'No data provided'})

        data = json.loads(raw_json)

        # Ensure it's in the list format expected by import logic
        if isinstance(data, dict):
            data = [data]

        user = request.user
        dietary_count = 0
        exercise_count = 0

        for entry in data:
            if not isinstance(entry, dict):
                continue

            date_str = entry.get('date')
            if not date_str:
                continue

            try:
                entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                continue

            day_remarks = (entry.get('remarks') or "").strip()
            coach_feedback = (entry.get('coach_feedback') or "").strip()

            # Dietary items
            food_items = entry.get('dietary') or entry.get('food') or []
            if not isinstance(food_items, list):
                food_items = []

            is_first_item = True
            for item in food_items:
                if not isinstance(item, dict):
                    continue

                item_notes = (item.get('notes') or item.get('note') or "").strip()
                item_remarks = (item.get('remarks') or "").strip() or day_remarks

                # Use coach feedback as remarks for first item if available
                if is_first_item and coach_feedback:
                    item_remarks = coach_feedback
                    is_first_item = False

                create_kwargs = {
                    "user": user,
                    "date": entry_date,
                    "item": item.get("item", "") or "",
                    "calories": item.get("calories", 0) or 0,
                    "notes": item_notes,
                }

                if hasattr(DietaryEntry, "remarks"):
                    create_kwargs["remarks"] = item_remarks

                DietaryEntry.objects.create(**create_kwargs)
                dietary_count += 1

            # Exercise items
            exercise_items = entry.get('exercise') or []
            if not isinstance(exercise_items, list):
                exercise_items = []

            for ex in exercise_items:
                if not isinstance(ex, dict):
                    continue

                # Accept both duration_minutes (model field) and duration_min
                duration = ex.get('duration_minutes', None)
                if duration is None:
                    duration = ex.get('duration_min', 0)

                ex_remarks = (ex.get('remarks') or "").strip() or day_remarks

                ExerciseEntry.objects.create(
                    user=user,
                    date=entry_date,
                    activity=ex.get('activity', '') or '',
                    duration_minutes=duration or 0,
                    calories_burned=ex.get('calories_burned', 0) or 0,
                    remarks=ex_remarks
                )
                exercise_count += 1

        # Build success message
        messages = []
        if dietary_count > 0:
            messages.append(f'{dietary_count} food item(s)')
        if exercise_count > 0:
            messages.append(f'{exercise_count} exercise(s)')

        if messages:
            return JsonResponse({'success': True, 'message': f'Saved {" and ".join(messages)}.'})
        else:
            return JsonResponse({'success': False, 'error': 'No valid items to save'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def ai_quota_status(request):
    """Get user's current AI quota status."""
    # Check if user has AI access enabled
    if not hasattr(request.user, 'profile') or not request.user.profile.ai_enabled:
        return JsonResponse({'success': False, 'error': 'AI features not enabled for your account'}, status=403)

    quota_info = get_user_quota_info(request.user)
    return JsonResponse({
        'success': True,
        'quota': quota_info
    })
