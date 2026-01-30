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
from .models import DietaryEntry, ExerciseEntry, WeightEntry, UserProfile

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

    # Find the most recent entry date to base charts on actual data
    latest_dietary = DietaryEntry.objects.filter(user=target_user).aggregate(m=Max('date'))['m']
    latest_exercise = ExerciseEntry.objects.filter(user=target_user).aggregate(m=Max('date'))['m']
    latest_weight = WeightEntry.objects.filter(user=target_user).aggregate(m=Max('date'))['m']
    latest_dates = [d for d in [latest_dietary, latest_exercise, latest_weight, today] if d]

    if latest_dates:
        chart_end = max(latest_dates)
        chart_start = chart_end - timedelta(days=29)  # 30 days of data for scrollable charts
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
    # Build list [[date, count], ...]
    heatmap_data = [[d, c] for d, c in activity_counts.items()]

    # Summary stats
    total_calories = sum(cal_values)
    total_exercise_min = sum(ex_values)

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

            # Dietary list can be "dietary" OR "food"
            food_items = entry.get('dietary') or entry.get('food') or []
            if not isinstance(food_items, list):
                food_items = []

            for item in food_items:
                if not isinstance(item, dict):
                    continue

                # Some JSONs may put notes/note/remarks per item; fall back to day remarks
                item_notes = (item.get('notes') or item.get('note') or "").strip()
                item_remarks = (item.get('remarks') or "").strip() or day_remarks

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
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
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
        
        # Calculate totals
        total_calories_in = sum(d['calories'] or 0 for d in dietary)
        total_calories_burned = sum(e['calories_burned'] or 0 for e in exercise)
        total_exercise_min = sum(e['duration_minutes'] or 0 for e in exercise)
        
        # Convert Decimal to float for JSON serialization
        for w in weight:
            w['weight_kg'] = float(w['weight_kg'])
        
        # Find a remarks string to use at the top level (first non-empty from dietary or exercise)
        remarks = ""
        if dietary and dietary[0].get('remarks'):
            remarks = dietary[0]['remarks']
        elif exercise and exercise[0].get('remarks'):
            remarks = exercise[0]['remarks']

        return JsonResponse({
            'success': True,
            'date': date_str,
            'dietary': dietary,
            'exercise': exercise,
            'weight': weight,
            'remarks': remarks,
            'summary': {
                'total_calories_in': total_calories_in,
                'total_calories_burned': total_calories_burned,
                'total_exercise_min': total_exercise_min,
                'net_calories': total_calories_in - total_calories_burned
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
        service = AIFoodLogService()

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

            # Dietary items
            food_items = entry.get('dietary') or entry.get('food') or []
            if not isinstance(food_items, list):
                food_items = []

            for item in food_items:
                if not isinstance(item, dict):
                    continue

                item_notes = (item.get('notes') or item.get('note') or "").strip()
                item_remarks = (item.get('remarks') or "").strip() or day_remarks

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