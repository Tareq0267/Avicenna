import json
from collections import defaultdict
from datetime import timedelta, datetime
from decimal import Decimal

from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Max, Min
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib.auth import logout, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.cache import never_cache
from dateutil.relativedelta import relativedelta

from tracker.models import (
    DietaryEntry, ExerciseEntry, WeightEntry, UserProfile,
    Routine, CompletionRecord,
)
from tracker.services.calorie_calculator import get_calorie_status
from tracker.routine_presets import get_presets_by_group


def get_partner(user):
    """Get the partner user if linked, otherwise None."""
    try:
        profile = user.profile
        return profile.partner
    except UserProfile.DoesNotExist:
        return None


def _get_routine_streak(routine, user, today):
    """Calculate consecutive days of completion for a routine, ending at today or yesterday."""
    completion_dates = set(
        CompletionRecord.objects.filter(routine=routine, user=user, date__lte=today)
        .order_by('-date')
        .values_list('date', flat=True)[:60]  # Look back max 60 days
    )
    if not completion_dates:
        return 0

    # Start from today — if not completed today, start from yesterday
    check_date = today
    if check_date not in completion_dates:
        check_date = today - timedelta(days=1)
        if check_date not in completion_dates:
            return 0

    streak = 0
    while check_date in completion_dates:
        # Only count days where the routine was scheduled
        if routine.is_scheduled_for(check_date):
            streak += 1
        check_date -= timedelta(days=1)
        # Skip days where routine wasn't scheduled (don't break streak)
        while not routine.is_scheduled_for(check_date) and (today - check_date).days < 60:
            check_date -= timedelta(days=1)

    return streak


@login_required
@never_cache
def dashboard(request, view_partner=False):
    today = timezone.now().date()

    # Determine which user's data to show
    partner = get_partner(request.user)
    viewing_partner = view_partner and partner is not None
    target_user = partner if viewing_partner else request.user

    # Get calorie status for the target user
    calorie_status = get_calorie_status(target_user)

    # Find the full date range of entries to show all data in charts
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
            'streak': _get_routine_streak(routine, target_user, today),
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
        'routine_ring_dash': round(routine_done / routine_total * 97.4, 1) if routine_total > 0 else 0,
        'routine_icon_choices': routine_icon_choices,
        'routine_preset_groups': routine_preset_groups,
        'routine_existing_presets': routine_existing_presets,
        # Love letter (latest) for special users
        'latest_love_letter': _get_love_letters()[0],
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


def guide(request):
    """Display the getting started guide."""
    return render(request, 'tracker/guide.html')


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


def _get_love_letters():
    """Return love letter entries for special users (newest first)."""
    return [
        {
            'version': '4',
            'date': '22 March 2026',
            'title': 'Your Streaks Are on Fire',
            'greeting': 'Hii sayang~',
            'message': "I made your routines even more fun! Now every routine tracks your streak — how many days in a row you've completed it. And I added this cute little progress ring on your dashboard that fills up as you check things off.",
            'features': [
                'Fire streak badges on each routine (keep the flame alive!)',
                'Beautiful circular progress ring on your dashboard',
                'Smooth satisfying animations when you check things off',
                'Streaks are smart — weekend off-days won\'t break them',
            ],
            'closing': "Every streak you build makes me so proud of you. Keep going, I believe in you!",
            'sign_off': 'Always yours',
        },
        {
            'version': '3',
            'date': '22 March 2026',
            'title': 'Your Routines, My Love',
            'greeting': 'Hii sayang~',
            'message': "I added something new just for you! Now you can track your daily routines — Solat, skincare, exercise, everything! And your AI coach knows about them too, so she'll cheer you on.",
            'features': [
                'Daily routine tracker on your dashboard',
                'Pretty pastel color picker for your routines',
                'AI coach now sees your routine progress',
                'Your routines show up in the activity heatmap',
            ],
            'closing': 'I hope this helps you stay consistent, because you inspire me to be better every day.',
            'sign_off': 'Always yours',
        },
        {
            'version': '2',
            'date': '21 March 2026',
            'title': 'A New Home For You',
            'greeting': 'Hello my cutiepie~',
            'message': "I gave Avicenna a makeover! Everything is cleaner and prettier now. The settings page has your own profile with your cute little avatar.",
            'features': [
                'Beautiful new settings page with your profile',
                'Compact routine card right on your dashboard',
                'Charts now show ALL your data, not just 30 days',
                'Cleaner navbar — less clutter, more love',
            ],
            'closing': "Every pixel was placed with you in mind.",
            'sign_off': 'Love you always',
        },
        {
            'version': '1',
            'date': '15 March 2026',
            'title': 'The First Letter',
            'greeting': 'Hii my cutiepie Qaisara~',
            'message': "Since you are one of the most loyal Avicenna members, I have given you a special version of this app. For you only, it's Avicenna with love.",
            'features': [
                'UNOBSTRUCTED use of the AI feature',
                'Your very own pink theme',
                'This love letter system, just for you',
            ],
            'closing': "Remember to not overuse it okay sayang~",
            'sign_off': 'Love you',
        },
    ]


def _get_changelog():
    """Return the app changelog entries."""
    return [
        {
            'version': '2.2.0',
            'date': '2026-03-22',
            'title': 'Routine Streaks & Animations',
            'changes': [
                'Per-routine streak counter with fire badge — tracks consecutive days',
                'Circular progress ring replaces progress pill on dashboard',
                'Smooth check animations with satisfying bounce effects',
                'Streaks are smart — skips non-scheduled days without breaking',
            ],
        },
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
        'love_letters': _get_love_letters(),
    }
    return render(request, 'tracker/settings.html', context)


@login_required
@require_POST
def update_username(request):
    """Update the logged-in user's username."""
    new_username = request.POST.get('username', '').strip()
    if not new_username:
        return redirect('tracker:settings')
    if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
        return redirect('tracker:settings')
    request.user.username = new_username
    request.user.save()
    return redirect('tracker:settings')
