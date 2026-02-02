"""
Calorie Calculator using the Mifflin-St Jeor Equation.
Reference: https://www.calculator.net/calorie-calculator.html
"""

# Activity level multipliers for TDEE calculation
ACTIVITY_MULTIPLIERS = {
    'sedentary': 1.2,      # Little or no exercise
    'light': 1.375,        # Light exercise 1-3 days/week
    'moderate': 1.55,      # Moderate exercise 3-5 days/week
    'active': 1.725,       # Hard exercise 6-7 days/week
    'extra': 1.9,          # Very hard exercise + physical job
}

# Calorie adjustment for weight goals (per day)
CALORIE_ADJUSTMENT = 500  # ~0.5kg per week


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation.

    BMR (Men) = 10 × weight(kg) + 6.25 × height(cm) - 5 × age(years) + 5
    BMR (Women) = 10 × weight(kg) + 6.25 × height(cm) - 5 × age(years) - 161

    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: 'male' or 'female'

    Returns:
        BMR in calories per day
    """
    base_bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)

    if gender == 'male':
        return base_bmr + 5
    else:  # female
        return base_bmr - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Calculate Total Daily Energy Expenditure.

    Args:
        bmr: Basal Metabolic Rate
        activity_level: One of 'sedentary', 'light', 'moderate', 'active', 'extra'

    Returns:
        TDEE in calories per day
    """
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return bmr * multiplier


def calculate_daily_calorie_goal(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    fitness_goal: str
) -> int:
    """
    Calculate the daily calorie goal based on user profile and fitness goal.

    Args:
        weight_kg: Current weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: 'male' or 'female'
        activity_level: Activity level string
        fitness_goal: 'lose', 'gain', or 'maintain'

    Returns:
        Daily calorie goal as integer
    """
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, activity_level)

    if fitness_goal == 'lose':
        daily_goal = tdee - CALORIE_ADJUSTMENT
    elif fitness_goal == 'gain':
        daily_goal = tdee + CALORIE_ADJUSTMENT
    else:  # maintain
        daily_goal = tdee

    # Ensure minimum healthy calorie intake
    # Men should not go below 1500, women below 1200
    min_calories = 1500 if gender == 'male' else 1200
    daily_goal = max(daily_goal, min_calories)

    return round(daily_goal)


def calculate_calorie_goal_for_user(user):
    """
    Calculate daily calorie goal for a Django user.

    Pulls weight from the latest WeightEntry record.

    Args:
        user: Django User instance

    Returns:
        Daily calorie goal as integer, or None if profile incomplete
    """
    from .models import WeightEntry

    try:
        profile = user.profile
    except AttributeError:
        return None

    # Check if profile has required fields
    if not profile.is_calorie_profile_ready():
        return None

    # Get latest weight
    latest_weight = WeightEntry.objects.filter(user=user).order_by('-date').first()
    if not latest_weight:
        return None

    return calculate_daily_calorie_goal(
        weight_kg=float(latest_weight.weight_kg),
        height_cm=float(profile.height_cm),
        age=profile.age,
        gender=profile.gender,
        activity_level=profile.activity_level,
        fitness_goal=profile.fitness_goal
    )


def get_calorie_status(user):
    """
    Get the user's calorie status for today.

    Returns:
        dict with:
            - daily_goal: int or None
            - calories_consumed: int
            - calories_remaining: int (for lose/maintain) or calories_to_surpass (for gain)
            - fitness_goal: str
            - progress_percent: float (0-100+)
            - status: 'under', 'on_track', 'over'
    """
    from django.utils import timezone
    from django.db.models import Sum
    from .models import DietaryEntry

    today = timezone.now().date()

    # Get daily goal
    daily_goal = calculate_calorie_goal_for_user(user)
    if daily_goal is None:
        return None

    # Get today's consumed calories
    calories_consumed = DietaryEntry.objects.filter(
        user=user,
        date=today
    ).aggregate(total=Sum('calories'))['total'] or 0

    # Get fitness goal
    fitness_goal = user.profile.fitness_goal

    # Calculate remaining/surplus
    calories_remaining = daily_goal - calories_consumed
    progress_percent = (calories_consumed / daily_goal * 100) if daily_goal > 0 else 0

    # Determine status
    if fitness_goal == 'lose':
        # For weight loss: under is good, over is concerning
        if calories_remaining > 200:
            status = 'under'  # Good - still have calories left
        elif calories_remaining >= -100:
            status = 'on_track'  # Close to goal
        else:
            status = 'over'  # Over the limit
    elif fitness_goal == 'gain':
        # For weight gain: over is good, under needs more food
        if calories_remaining > 200:
            status = 'under'  # Need to eat more
        elif calories_remaining >= -100:
            status = 'on_track'  # Close to goal
        else:
            status = 'over'  # Good - surpassed goal
    else:  # maintain
        if abs(calories_remaining) <= 200:
            status = 'on_track'
        elif calories_remaining > 200:
            status = 'under'
        else:
            status = 'over'

    return {
        'daily_goal': daily_goal,
        'calories_consumed': calories_consumed,
        'calories_remaining': calories_remaining,
        'fitness_goal': fitness_goal,
        'progress_percent': min(progress_percent, 150),  # Cap at 150% for display
        'status': status,
    }
