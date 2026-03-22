from datetime import datetime
from decimal import Decimal

from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from tracker.models import (
    DietaryEntry, WeightEntry, ExerciseEntry, CompletionRecord,
    UserProfile, GOAL_CHOICES, GENDER_CHOICES, ACTIVITY_CHOICES,
)
from tracker.services.calorie_calculator import (
    calculate_daily_calorie_goal, calculate_calorie_goal_for_user,
)
from tracker.views.core import get_partner


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
def delete_weight_entry(request, entry_id):
    try:
        entry = WeightEntry.objects.get(id=entry_id, user=request.user)
    except WeightEntry.DoesNotExist:
        return HttpResponseForbidden()
    entry.delete()
    return redirect('tracker:dashboard')


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


@login_required
def calorie_setup(request):
    """Calorie goal setup wizard."""
    from django.shortcuts import render

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
