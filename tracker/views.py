from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
@login_required
@require_POST
def delete_dietary_entry(request, entry_id):
    try:
        entry = DietaryEntry.objects.get(id=entry_id, user=request.user)
    except DietaryEntry.DoesNotExist:
        return HttpResponseForbidden()
    entry.delete()
    return redirect('tracker:dashboard')

@login_required
@require_POST
def delete_exercise_entry(request, entry_id):
    try:
        entry = ExerciseEntry.objects.get(id=entry_id, user=request.user)
    except ExerciseEntry.DoesNotExist:
        return HttpResponseForbidden()
    entry.delete()
    return redirect('tracker:dashboard')

@login_required
@require_POST
def delete_weight_entry(request, entry_id):
    try:
        entry = WeightEntry.objects.get(id=entry_id, user=request.user)
    except WeightEntry.DoesNotExist:
        return HttpResponseForbidden()
    entry.delete()
    return redirect('tracker:dashboard')
from django.contrib.auth import logout, login
from django.contrib.auth.forms import UserCreationForm

# Custom logout view to guarantee session is cleared
def custom_logout(request):
    logout(request)
    return redirect('/accounts/login/')


def register(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('tracker:dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('tracker:dashboard')
        else:
            # Return errors as JSON for AJAX handling
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = list(error_list)
            return JsonResponse({'success': False, 'errors': errors})

    return redirect('/accounts/login/')
import json
from collections import defaultdict
from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Max
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from .models import DietaryEntry, ExerciseEntry, WeightEntry, UserProfile, Routine, CompletionRecord

from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required


from django.views.decorators.cache import never_cache

def get_partner(user):
    """Get the partner user if linked, otherwise None."""
    try:
        profile = user.profile
        return profile.partner
    except UserProfile.DoesNotExist:
        return None


@login_required
@never_cache
def dashboard(request, view_partner=False):
    today = timezone.now().date()

    # Determine which user's data to show
    partner = get_partner(request.user)
    viewing_partner = view_partner and partner is not None
    target_user = partner if viewing_partner else request.user

    # Get calorie status for the target user
    from .calorie_calculator import get_calorie_status
    calorie_status = get_calorie_status(target_user)

    # Find the full date range of entries to show all data in charts
    from django.db.models import Min
    earliest_dietary = DietaryEntry.objects.filter(user=target_user).aggregate(m=Min('date'))['m']
    earliest_exercise = ExerciseEntry.objects.filter(user=target_user).aggregate(m=Min('date'))['m']
    earliest_weight = WeightEntry.objects.filter(user=target_user).aggregate(m=Min('date'))['m']
    latest_dietary = DietaryEntry.objects.filter(user=target_user).aggregate(m=Max('date'))['m']
    latest_exercise = ExerciseEntry.objects.filter(user=target_user).aggregate(m=Max('date'))['m']
    latest_weight = WeightEntry.objects.filter(user=target_user).aggregate(m=Max('date'))['m']

    earliest_routine = CompletionRecord.objects.filter(user=target_user).aggregate(m=Min('date'))['m']
    latest_routine = CompletionRecord.objects.filter(user=target_user).aggregate(m=Max('date'))['m']

    earliest_dates = [d for d in [earliest_dietary, earliest_exercise, earliest_weight, earliest_routine] if d]
    latest_dates = [d for d in [latest_dietary, latest_exercise, latest_weight, latest_routine, today] if d]

    if earliest_dates:
        chart_start = min(earliest_dates)
        chart_end = max(latest_dates)
    else:
        chart_end = today
        chart_start = today - timedelta(days=29)

    # --- recent entries for tables (target user) ---
    dietary_recent = DietaryEntry.objects.filter(user=target_user).order_by('-date', '-id')[:25]
    exercise_recent = ExerciseEntry.objects.filter(user=target_user).order_by('-date', '-id')[:15]
    weight_recent = WeightEntry.objects.filter(user=target_user).order_by('-date')[:10]

    # --- aggregate data for charts (based on actual data range) ---
    # Calories per day (line chart)
    cal_qs = (
        DietaryEntry.objects.filter(user=target_user, date__gte=chart_start, date__lte=chart_end)
        .values('date')
        .annotate(total=Sum('calories'))
        .order_by('date')
    )
    cal_dates = [str(r['date']) for r in cal_qs]
    cal_values = [r['total'] or 0 for r in cal_qs]

    # Exercise minutes per day (bar chart)
    ex_qs = (
        ExerciseEntry.objects.filter(user=target_user, date__gte=chart_start, date__lte=chart_end)
        .values('date')
        .annotate(total=Sum('duration_minutes'))
        .order_by('date')
    )
    ex_dates = [str(r['date']) for r in ex_qs]
    ex_values = [r['total'] or 0 for r in ex_qs]

    # Weight trend (line chart) - show all weight data in range
    wt_qs = WeightEntry.objects.filter(user=target_user, date__gte=chart_start, date__lte=chart_end).order_by('date')
    wt_dates = [str(w.date) for w in wt_qs]
    wt_values = [float(w.weight_kg) for w in wt_qs]

    # Get latest weight (regardless of date range)
    latest_weight_entry = WeightEntry.objects.filter(user=target_user).order_by('-date').first()
    latest_weight_value = float(latest_weight_entry.weight_kg) if latest_weight_entry else None

    # --- Heatmap: activity count per day (12 months back for navigation) ---
    from dateutil.relativedelta import relativedelta
    heatmap_start = (today - relativedelta(months=11)).replace(day=1)  # 12 months of data
    # End at last day of current month
    heatmap_end = (today + relativedelta(months=1)).replace(day=1) - timedelta(days=1)

    activity_counts = defaultdict(int)
    # count dietary entries
    for r in DietaryEntry.objects.filter(user=target_user, date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # count exercise entries
    for r in ExerciseEntry.objects.filter(user=target_user, date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # count weight entries
    for r in WeightEntry.objects.filter(user=target_user, date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # count routine completions
    for r in CompletionRecord.objects.filter(user=target_user, date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # Build list [[date, count], ...]
    heatmap_data = [[d, c] for d, c in activity_counts.items()]

    # Summary stats
    total_calories = sum(cal_values)
    total_exercise_min = sum(ex_values)

    # Check if user's calorie profile is complete
    try:
        calorie_profile_complete = target_user.profile.calorie_profile_complete
    except (AttributeError, UserProfile.DoesNotExist):
        calorie_profile_complete = False

    # Routine data for dashboard card (show for both own and partner views)
    routine_checklist = []
    routine_total = 0
    routine_done = 0
    routine_icon_choices = []
    routine_preset_groups = {}
    routine_existing_presets = set()
    all_routines = Routine.objects.filter(user=target_user, is_active=True)
    todays_routines = [r for r in all_routines if r.is_scheduled_for(today)]
    def _sort_key(r):
        t = r.get_scheduled_time()
        return (t if t else '99:99', r.order)
    todays_routines.sort(key=_sort_key)
    completed_ids = set(
        CompletionRecord.objects.filter(user=target_user, date=today)
        .values_list('routine_id', flat=True)
    )
    for routine in todays_routines:
        routine_checklist.append({
            'routine': routine,
            'completed': routine.id in completed_ids,
        })
    routine_total = len(todays_routines)
    routine_done = len([c for c in routine_checklist if c['completed']])
    if not viewing_partner:
        routine_icon_choices = [
            'bi-check-circle', 'bi-star', 'bi-heart', 'bi-lightning-charge',
            'bi-book', 'bi-moon-stars', 'bi-sun', 'bi-droplet', 'bi-cup-straw',
            'bi-bicycle', 'bi-person-walking', 'bi-pencil', 'bi-music-note',
            'bi-palette', 'bi-code-slash', 'bi-camera', 'bi-chat-dots',
            'bi-clock', 'bi-trophy',
        ]
        from .routine_presets import get_presets_by_group
        routine_preset_groups = get_presets_by_group()
        routine_existing_presets = set(
            Routine.objects.filter(user=request.user, is_active=True, preset_key__gt='')
            .values_list('preset_key', flat=True)
        )

    context = {
        'dietary_recent': dietary_recent,
        'exercise_recent': exercise_recent,
        'weight_recent': weight_recent,
        'dietary_count': dietary_recent.count(),
        'exercise_count': exercise_recent.count(),
        'weight_count': weight_recent.count(),
        # chart data as JSON
        'cal_dates': json.dumps(cal_dates),
        'cal_values': json.dumps(cal_values),
        'ex_dates': json.dumps(ex_dates),
        'ex_values': json.dumps(ex_values),
        'wt_dates': json.dumps(wt_dates),
        'wt_values': json.dumps(wt_values),
        # heatmap (3 months)
        'heatmap_data': json.dumps(heatmap_data),
        'heatmap_start': str(heatmap_start),
        'heatmap_end': str(heatmap_end),
        'today': str(today),
        # summary
        'total_calories': total_calories,
        'total_exercise_min': total_exercise_min,
        'latest_weight': latest_weight_value,
        # Partner/couples mode
        'viewing_partner': viewing_partner,
        'partner': partner,
        'partner_name': partner.username if partner else None,
        'target_user': target_user,
        # Calorie tracking
        'calorie_status': calorie_status,
        'calorie_profile_complete': calorie_profile_complete,
        # Routine card
        'routine_checklist': routine_checklist,
        'routine_total': routine_total,
        'routine_done': routine_done,
        'routine_icon_choices': routine_icon_choices,
        'routine_preset_groups': routine_preset_groups,
        'routine_existing_presets': routine_existing_presets,
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
@never_cache
def partner_dashboard(request):
    """View partner's dashboard (read-only)."""
    return dashboard(request, view_partner=True)


@require_POST
@login_required
def import_json(request):
    """Import activity data from JSON (dietary and exercise entries)."""
    try:
        raw_json = request.POST.get('json_data', '').strip()
        if not raw_json:
            return JsonResponse({'success': False, 'error': 'No JSON data provided'})

        data = json.loads(raw_json)
        if not isinstance(data, list):
            return JsonResponse({'success': False, 'error': 'JSON must be a list/array of day objects'})

        user = request.user
        dietary_count = 0
        exercise_count = 0
        skipped_days = 0

        for entry in data:
            if not isinstance(entry, dict):
                skipped_days += 1
                continue

            date_str = entry.get('date')
            if not date_str:
                skipped_days += 1
                continue

            try:
                entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                skipped_days += 1
                continue

            # Day-level remarks (applies to all items for that date)
            day_remarks = (entry.get('remarks') or "").strip()
            coach_feedback = (entry.get('coach_feedback') or "").strip()

            # Dietary list can be "dietary" OR "food"
            food_items = entry.get('dietary') or entry.get('food') or []
            if not isinstance(food_items, list):
                food_items = []

            is_first_item = True
            for item in food_items:
                if not isinstance(item, dict):
                    continue

                # Some JSONs may put notes/note/remarks per item; fall back to day remarks
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

                # Only set remarks if the model actually has that field
                if hasattr(DietaryEntry, "remarks"):
                    create_kwargs["remarks"] = item_remarks

                DietaryEntry.objects.create(**create_kwargs)
                dietary_count += 1

            # Exercise list
            exercise_items = entry.get('exercise') or []
            if not isinstance(exercise_items, list):
                exercise_items = []

            for ex in exercise_items:
                if not isinstance(ex, dict):
                    continue

                # Accept both duration_minutes (your model) and duration_min (your sample JSON)
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

        msg = f'Imported {dietary_count} dietary and {exercise_count} exercise entries.'
        if skipped_days:
            msg += f' Skipped {skipped_days} invalid day record(s).'

        return JsonResponse({'success': True, 'message': msg})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON (could not parse).'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



@require_POST
@login_required
@login_required
def add_weight(request):
    """Add a new weight entry."""
    try:
        weight_kg = request.POST.get('weight_kg', '').strip()
        date_str = request.POST.get('date', '').strip()
        notes = request.POST.get('notes', '').strip()
        if not weight_kg:
            return JsonResponse({'success': False, 'error': 'Weight is required'})
        user = request.user
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.localtime().date()
        WeightEntry.objects.create(
            user=user,
            date=entry_date,
            weight_kg=Decimal(weight_kg),
            notes=notes
        )
        return JsonResponse({'success': True, 'message': f'Weight {weight_kg} kg recorded for {entry_date}.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def guide(request):
    """Display the getting started guide."""
    return render(request, 'tracker/guide.html')


@login_required
def daily_recap(request, date_str, user_id=None):
    """Get daily recap data for a specific date."""
    try:
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Determine which user's data to fetch
        if user_id:
            # Verify the user_id is the current user's partner
            partner = get_partner(request.user)
            if partner and partner.id == user_id:
                target_user = partner
            else:
                return JsonResponse({'success': False, 'error': 'Unauthorized'})
        else:
            target_user = request.user

        # Get all entries for this date
        dietary = list(DietaryEntry.objects.filter(user=target_user, date=entry_date).values(
            'item', 'calories', 'notes', 'remarks'
        ))
        exercise = list(ExerciseEntry.objects.filter(user=target_user, date=entry_date).values(
            'activity', 'duration_minutes', 'calories_burned', 'remarks'
        ))
        weight = list(WeightEntry.objects.filter(user=target_user, date=entry_date).values(
            'weight_kg', 'notes'
        ))
        
        # Get routine completions for this date
        routine_completions = list(
            CompletionRecord.objects.filter(user=target_user, date=entry_date)
            .select_related('routine')
            .order_by('completed_at')
        )
        routines = [{
            'name': rc.routine.name,
            'icon': rc.routine.icon,
            'color': rc.routine.color,
        } for rc in routine_completions]

        # Calculate totals
        total_calories_in = sum(d['calories'] or 0 for d in dietary)
        total_calories_burned = sum(e['calories_burned'] or 0 for e in exercise)
        total_exercise_min = sum(e['duration_minutes'] or 0 for e in exercise)

        # Convert Decimal to float for JSON serialization
        for w in weight:
            w['weight_kg'] = float(w['weight_kg'])

        # Collect all unique non-empty remarks from dietary and exercise entries
        all_remarks = []
        seen_remarks = set()

        # Gather remarks from dietary entries
        for d in dietary:
            remark = (d.get('remarks') or '').strip()
            if remark and remark not in seen_remarks:
                all_remarks.append(remark)
                seen_remarks.add(remark)

        # Gather remarks from exercise entries
        for e in exercise:
            remark = (e.get('remarks') or '').strip()
            if remark and remark not in seen_remarks:
                all_remarks.append(remark)
                seen_remarks.add(remark)

        return JsonResponse({
            'success': True,
            'date': date_str,
            'dietary': dietary,
            'exercise': exercise,
            'weight': weight,
            'routines': routines,
            'all_remarks': all_remarks,
            'summary': {
                'total_calories_in': total_calories_in,
                'total_calories_burned': total_calories_burned,
                'total_exercise_min': total_exercise_min,
                'net_calories': total_calories_in - total_calories_burned,
                'routines_completed': len(routines),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# --- AI Food Logging Views ---

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

    from .rate_limit import ai_rate_limit, log_ai_usage

    # Apply rate limiting manually (since we need to log usage after)
    from .rate_limit import check_rate_limit
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
        from .ai_service import AIFoodLogService
        from .calorie_calculator import get_calorie_status

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

    from .rate_limit import get_user_quota_info

    quota_info = get_user_quota_info(request.user)
    return JsonResponse({
        'success': True,
        'quota': quota_info
    })


# --- Calorie Goal Setup Views ---

@login_required
def calorie_setup(request):
    """Calorie goal setup wizard."""
    from .calorie_calculator import calculate_daily_calorie_goal
    from .models import GOAL_CHOICES, GENDER_CHOICES, ACTIVITY_CHOICES

    profile = request.user.profile

    if request.method == 'POST':
        # Get form data
        fitness_goal = request.POST.get('fitness_goal')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        height_cm = request.POST.get('height_cm')
        activity_level = request.POST.get('activity_level')
        initial_weight = request.POST.get('initial_weight')

        errors = {}

        # Validate required fields
        if not fitness_goal:
            errors['fitness_goal'] = 'Please select your goal'
        if not age or not age.isdigit() or int(age) < 10 or int(age) > 120:
            errors['age'] = 'Please enter a valid age (10-120)'
        if not gender:
            errors['gender'] = 'Please select your gender'
        if not height_cm:
            errors['height_cm'] = 'Please enter your height'
        else:
            try:
                h = float(height_cm)
                if h < 50 or h > 300:
                    errors['height_cm'] = 'Please enter a valid height (50-300 cm)'
            except ValueError:
                errors['height_cm'] = 'Please enter a valid number'
        if not activity_level:
            errors['activity_level'] = 'Please select your activity level'

        # Check for initial weight if no weight entries exist
        latest_weight = WeightEntry.objects.filter(user=request.user).order_by('-date').first()
        if not latest_weight:
            if not initial_weight:
                errors['initial_weight'] = 'Please enter your current weight'
            else:
                try:
                    w = float(initial_weight)
                    if w < 20 or w > 500:
                        errors['initial_weight'] = 'Please enter a valid weight (20-500 kg)'
                except ValueError:
                    errors['initial_weight'] = 'Please enter a valid number'

        if errors:
            return JsonResponse({'success': False, 'errors': errors})

        # Create initial weight entry if needed
        if not latest_weight and initial_weight:
            WeightEntry.objects.create(
                user=request.user,
                date=timezone.now().date(),
                weight_kg=Decimal(initial_weight),
                notes='Initial weight from calorie setup'
            )

        # Update profile
        profile.fitness_goal = fitness_goal
        profile.age = int(age)
        profile.gender = gender
        profile.height_cm = Decimal(height_cm)
        profile.activity_level = activity_level
        profile.calorie_profile_complete = True

        # Calculate and save daily calorie goal
        latest_weight = WeightEntry.objects.filter(user=request.user).order_by('-date').first()
        if latest_weight:
            daily_goal = calculate_daily_calorie_goal(
                weight_kg=float(latest_weight.weight_kg),
                height_cm=float(height_cm),
                age=int(age),
                gender=gender,
                activity_level=activity_level,
                fitness_goal=fitness_goal
            )
            profile.daily_calorie_goal = daily_goal

        profile.save()

        return JsonResponse({
            'success': True,
            'message': 'Calorie goal set successfully!',
            'daily_goal': profile.daily_calorie_goal,
            'redirect': '/tracker/dashboard/'
        })

    # GET request - render the setup page
    latest_weight = WeightEntry.objects.filter(user=request.user).order_by('-date').first()

    context = {
        'goal_choices': GOAL_CHOICES,
        'gender_choices': GENDER_CHOICES,
        'activity_choices': ACTIVITY_CHOICES,
        'profile': profile,
        'latest_weight': float(latest_weight.weight_kg) if latest_weight else None,
    }
    return render(request, 'tracker/calorie_setup.html', context)


@require_POST
@login_required
def update_calorie_settings(request):
    """Update calorie settings from dashboard modal."""
    from .calorie_calculator import calculate_calorie_goal_for_user

    profile = request.user.profile

    # Update fields if provided
    fitness_goal = request.POST.get('fitness_goal')
    activity_level = request.POST.get('activity_level')
    age = request.POST.get('age')

    if fitness_goal:
        profile.fitness_goal = fitness_goal
    if activity_level:
        profile.activity_level = activity_level
    if age and age.isdigit():
        profile.age = int(age)

    profile.save()

    # Recalculate daily goal
    new_goal = calculate_calorie_goal_for_user(request.user)
    if new_goal:
        profile.daily_calorie_goal = new_goal
        profile.save()

    return JsonResponse({
        'success': True,
        'message': 'Settings updated!',
        'daily_goal': profile.daily_calorie_goal
    })


# ===== Routine Tracker Views =====

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
    from .routine_presets import get_presets_by_group
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

    return JsonResponse({
        'success': True,
        'completed': completed,
        'trigger_confetti': completed,
        'all_done': all_done,
        'done_today': completed_count,
        'total_today': len(todays_routines),
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
        color=request.POST.get('color', '#6366f1'),
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
    from .routine_presets import add_preset_for_user, add_preset_group_for_user

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


def _get_changelog():
    """Return the app changelog entries."""
    return [
        {
            'version': '2.1.0',
            'date': '2026-03-22',
            'title': 'Settings & Dashboard Revamp',
            'changes': [
                'New settings page with profile avatar and username editing',
                'Routine tracker moved to dashboard as a compact card',
                'Simplified navbar — Guide, Changelog, and Logout consolidated into Settings',
                'Redesigned changelog with collapsible previous updates',
                'Charts now show all entries instead of last 30 days',
            ],
        },
        {
            'version': '2.0.0',
            'date': '2026-03-21',
            'title': 'Routine Tracker & Gamification',
            'changes': [
                'New routine tracker with daily/weekly/monthly scheduling',
                'Pre-built presets: Solat (5 daily prayers), Exercise, Shower, and more',
                'Completion tracking with confetti celebrations',
                'Confetti celebration on routine completion',
            ],
        },
        {
            'version': '1.3.0',
            'date': '2026-03-15',
            'title': 'Special User Features',
            'changes': [
                'Unlimited AI access for special users',
                'Personalized pink theme',
                'Custom rate limits',
            ],
        },
        {
            'version': '1.2.0',
            'date': '2026-03-01',
            'title': 'Calorie Tracking',
            'changes': [
                'Calorie setup wizard with BMR/TDEE calculation',
                'Daily calorie goal tracking on dashboard',
                'Calorie settings modal for quick updates',
            ],
        },
        {
            'version': '1.1.0',
            'date': '2026-02-15',
            'title': 'AI Food Logging',
            'changes': [
                'AI-powered food logging with text and image input',
                'GPT-4o integration for food recognition',
                'Usage rate limiting and quota tracking',
                'Personalized coach feedback',
            ],
        },
        {
            'version': '1.0.0',
            'date': '2026-01-01',
            'title': 'Initial Release',
            'changes': [
                'Dietary entry tracking',
                'Exercise logging',
                'Weight tracking with trend charts',
                'Dashboard with heatmap and charts',
                'Couples mode for partner viewing',
                'JSON data import',
            ],
        },
    ]


@login_required
def update_log(request):
    """Render the changelog / update log page."""
    return render(request, 'tracker/update_log.html', {'changelog': _get_changelog()})


@login_required
def settings_page(request):
    """Settings page combining Guide, Changelog, and Account actions."""
    context = {
        'changelog': _get_changelog(),
    }
    return render(request, 'tracker/settings.html', context)


@login_required
@require_POST
def update_username(request):
    """Update the logged-in user's username."""
    from django.contrib.auth.models import User
    new_username = request.POST.get('username', '').strip()
    if not new_username:
        return redirect('tracker:settings')
    if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
        return redirect('tracker:settings')
    request.user.username = new_username
    request.user.save()
    return redirect('tracker:settings')