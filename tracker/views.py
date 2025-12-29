from django.contrib.auth import logout

# Custom logout view to guarantee session is cleared
def custom_logout(request):
    logout(request)
    return redirect('/accounts/login/')
import json
from collections import defaultdict
from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Max
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from .models import DietaryEntry, ExerciseEntry, WeightEntry

from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required


from django.views.decorators.cache import never_cache

@login_required
@never_cache
def dashboard(request):
    today = timezone.now().date()

    # Find the most recent entry date to base charts on actual data
    latest_dietary = DietaryEntry.objects.aggregate(m=Max('date'))['m']
    latest_exercise = ExerciseEntry.objects.aggregate(m=Max('date'))['m']
    latest_dates = [d for d in [latest_dietary, latest_exercise] if d]
    
    if latest_dates:
        chart_end = max(latest_dates)
        chart_start = chart_end - timedelta(days=6)  # 7 days of data
    else:
        chart_end = today
        chart_start = today - timedelta(days=6)

    # --- recent entries for tables (user-specific) ---
    dietary_recent = DietaryEntry.objects.filter(user=request.user).order_by('-date', '-id')[:25]
    exercise_recent = ExerciseEntry.objects.filter(user=request.user).order_by('-date', '-id')[:15]
    weight_recent = WeightEntry.objects.filter(user=request.user).order_by('-date')[:10]

    # --- aggregate data for charts (based on actual data range) ---
    # Calories per day (line chart)
    cal_qs = (
        DietaryEntry.objects.filter(user=request.user, date__gte=chart_start, date__lte=chart_end)
        .values('date')
        .annotate(total=Sum('calories'))
        .order_by('date')
    )
    cal_dates = [str(r['date']) for r in cal_qs]
    cal_values = [r['total'] or 0 for r in cal_qs]

    # Exercise minutes per day (bar chart)
    ex_qs = (
        ExerciseEntry.objects.filter(user=request.user, date__gte=chart_start, date__lte=chart_end)
        .values('date')
        .annotate(total=Sum('duration_minutes'))
        .order_by('date')
    )
    ex_dates = [str(r['date']) for r in ex_qs]
    ex_values = [r['total'] or 0 for r in ex_qs]

    # Weight trend (line chart) - show all available data
    wt_qs = WeightEntry.objects.filter(user=request.user, date__gte=chart_start, date__lte=chart_end).order_by('date')
    wt_dates = [str(w.date) for w in wt_qs]
    wt_values = [float(w.weight_kg) for w in wt_qs]

    # --- Heatmap: activity count per day (6 months starting with current month) ---
    # December, January, February, March, April, May (current month first, then 5 forward)
    from dateutil.relativedelta import relativedelta
    heatmap_start = today.replace(day=1)  # First day of current month (December)
    # End at last day of 5 months ahead
    heatmap_end_month = heatmap_start + relativedelta(months=5)  # May
    heatmap_end = (heatmap_end_month + relativedelta(months=1)).replace(day=1) - timedelta(days=1)

    activity_counts = defaultdict(int)
    # count dietary entries
    for r in DietaryEntry.objects.filter(user=request.user, date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # count exercise entries
    for r in ExerciseEntry.objects.filter(user=request.user, date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # count weight entries
    for r in WeightEntry.objects.filter(user=request.user, date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # Build list [[date, count], ...]
    heatmap_data = [[d, c] for d, c in activity_counts.items()]

    # Summary stats
    total_calories = sum(cal_values)
    total_exercise_min = sum(ex_values)
    latest_weight = wt_values[-1] if wt_values else None

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
        'latest_weight': latest_weight,
    }
    return render(request, 'tracker/dashboard.html', context)


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


@login_required
def daily_recap(request, date_str):
    """Get daily recap data for a specific date."""
    try:
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get all entries for this date
        dietary = list(DietaryEntry.objects.filter(date=entry_date).values(
            'item', 'calories', 'notes', 'remarks'
        ))
        exercise = list(ExerciseEntry.objects.filter(date=entry_date).values(
            'activity', 'duration_minutes', 'calories_burned', 'remarks'
        ))
        weight = list(WeightEntry.objects.filter(date=entry_date).values(
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