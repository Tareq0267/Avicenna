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

    # --- recent entries for tables ---
    dietary_recent = DietaryEntry.objects.all().order_by('-date', '-id')[:25]
    exercise_recent = ExerciseEntry.objects.all().order_by('-date', '-id')[:15]
    weight_recent = WeightEntry.objects.all().order_by('-date')[:10]

    # --- aggregate data for charts (based on actual data range) ---
    # Calories per day (line chart)
    cal_qs = (
        DietaryEntry.objects.filter(date__gte=chart_start, date__lte=chart_end)
        .values('date')
        .annotate(total=Sum('calories'))
        .order_by('date')
    )
    cal_dates = [str(r['date']) for r in cal_qs]
    cal_values = [r['total'] or 0 for r in cal_qs]

    # Exercise minutes per day (bar chart)
    ex_qs = (
        ExerciseEntry.objects.filter(date__gte=chart_start, date__lte=chart_end)
        .values('date')
        .annotate(total=Sum('duration_minutes'))
        .order_by('date')
    )
    ex_dates = [str(r['date']) for r in ex_qs]
    ex_values = [r['total'] or 0 for r in ex_qs]

    # Weight trend (line chart) - show all available data
    wt_qs = WeightEntry.objects.filter(date__gte=chart_start, date__lte=chart_end).order_by('date')
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
    for r in DietaryEntry.objects.filter(date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # count exercise entries
    for r in ExerciseEntry.objects.filter(date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
        activity_counts[str(r['date'])] += r['c']
    # count weight entries
    for r in WeightEntry.objects.filter(date__gte=heatmap_start, date__lte=heatmap_end).values('date').annotate(c=Count('id')):
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
def import_json(request):
    """Import activity data from JSON (dietary and exercise entries)."""
    try:
        raw_json = request.POST.get('json_data', '').strip()
        if not raw_json:
            return JsonResponse({'success': False, 'error': 'No JSON data provided'})
        
        data = json.loads(raw_json)
        
        # Get or create a default user
        user, _ = User.objects.get_or_create(username='admin')
        
        dietary_count = 0
        exercise_count = 0
        
        for entry in data:
            date_str = entry.get('date')
            if not date_str:
                continue
            entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Day-level remarks
            day_remarks = entry.get('remarks', '')
            
            # Dietary entries (supports both 'dietary' and 'food' keys)
            food_items = entry.get('dietary') or entry.get('food') or []
            for item in food_items:
                DietaryEntry.objects.create(
                    user=user,
                    date=entry_date,
                    item=item.get('item', ''),
                    calories=item.get('calories', 0),
                    notes=item.get('notes') or item.get('note', ''),  # support both 'notes' and 'note'
                    remarks=item.get('remarks') or day_remarks  # use item remarks or day remarks
                )
                dietary_count += 1
            
            # Exercise entries
            exercise_items = entry.get('exercise') or []
            for ex in exercise_items:
                ExerciseEntry.objects.create(
                    user=user,
                    date=entry_date,
                    activity=ex.get('activity', ''),
                    duration_minutes=ex.get('duration_minutes') or ex.get('duration_min', 0),  # support both
                    calories_burned=ex.get('calories_burned', 0),
                    remarks=ex.get('remarks') or day_remarks  # use exercise remarks or day remarks
                )
                exercise_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Imported {dietary_count} dietary entries and {exercise_count} exercise entries.'
        })
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'Invalid JSON: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
def add_weight(request):
    """Add a new weight entry."""
    try:
        weight_kg = request.POST.get('weight_kg', '').strip()
        date_str = request.POST.get('date', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        if not weight_kg:
            return JsonResponse({'success': False, 'error': 'Weight is required'})
        
        # Get or create a default user
        user, _ = User.objects.get_or_create(username='admin')
        
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
        
        return JsonResponse({
            'success': True,
            'date': date_str,
            'dietary': dietary,
            'exercise': exercise,
            'weight': weight,
            'summary': {
                'total_calories_in': total_calories_in,
                'total_calories_burned': total_calories_burned,
                'total_exercise_min': total_exercise_min,
                'net_calories': total_calories_in - total_calories_burned
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})