#!/usr/bin/env python
"""
Import activity log JSON into the database.
Run: python import_activity_log.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avicenna_project.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from tracker.models import DietaryEntry, ExerciseEntry

User = get_user_model()

# Your activity log data
DATA = [
  {
    "date": "2025-12-01",
    "food": [
      { "item": "2 plates rice + 2 kembung fish", "calories": 900, "note": "vomited roughly half" },
      { "item": "McD tomato chicken wrap", "calories": 350 },
      { "item": "Bihun sup daging", "calories": 450 }
    ],
    "exercise": [
      { "activity": "Jogging in place", "duration_min": 60, "calories_burned": 450 }
    ],
    "remarks": "High intake earlier but strong cardio; vomiting noted (not recommended). Net day roughly balanced."
  },
  {
    "date": "2025-12-02",
    "food": [
      { "item": "Salmon onigiri", "calories": 180 },
      { "item": "BBQ sausage (small)", "calories": 120 },
      { "item": "Half donut", "calories": 150 },
      { "item": "2 slices bread + cheese + thousand island", "calories": 400 },
      { "item": "Bihun sup beef", "calories": 450 }
    ],
    "exercise": [
      { "activity": "Jogging in place", "duration_min": 30, "calories_burned": 220 }
    ],
    "remarks": "Moderate calories, hunger signals increasing; workload accumulating."
  },
  {
    "date": "2025-12-03",
    "food": [
      { "item": "Salmon onigiri", "calories": 180 },
      { "item": "Ramen (broth not finished)", "calories": 450 },
      { "item": "Popcorn chicken", "calories": 350 }
    ],
    "exercise": [],
    "remarks": "Late work day, no exercise; intake reasonable considering fatigue."
  },
  {
    "date": "2025-12-04",
    "food": [
      { "item": "Nasi lemak", "calories": 600 },
      { "item": "Caesar salad", "calories": 300 },
      { "item": "Half medium chicken", "calories": 350 }
    ],
    "exercise": [
      { "activity": "Jogging in place", "duration_min": 60, "calories_burned": 500 }
    ],
    "remarks": "Very good balance day; high protein + high activity."
  },
  {
    "date": "2025-12-05",
    "food": [
      { "item": "Maggi tomyam", "calories": 380 },
      { "item": "Naan", "calories": 260 },
      { "item": "Tandoori chicken", "calories": 350 }
    ],
    "exercise": [
      { "activity": "Walking (heavy)", "duration_min": 90, "calories_burned": 350 }
    ],
    "remarks": "High sodium but protein saved the day; walking offset intake."
  },
  {
    "date": "2025-12-06",
    "food": [
      { "item": "Sausage roll", "calories": 300 },
      { "item": "Buffet beef, lamb, chicken", "calories": 1200 }
    ],
    "exercise": [
      { "activity": "Jogging in place", "duration_min": 30, "calories_burned": 230 }
    ],
    "remarks": "Heavy protein buffet; skipping dinner + JIP helped control surplus."
  },
  {
    "date": "2025-12-07",
    "food": [
      { "item": "Nasi kukus ayam goreng", "calories": 650 },
      { "item": "Maggi goreng ayam", "calories": 500 },
      { "item": "Chocolate (3 squares)", "calories": 150 }
    ],
    "exercise": [
      { "activity": "Jogging in place", "duration_min": 60, "calories_burned": 480 }
    ],
    "remarks": "Very high hunger day; carbs heavy but compensated with long cardio."
  },
  {
    "date": "2025-12-08",
    "food": [
      { "item": "Nasi biryani kambing (3 plates)", "calories": 1800 }
    ],
    "exercise": [
      { "activity": "Dumbbell workout (4.5kg each)", "duration_min": 20, "calories_burned": 180 }
    ],
    "remarks": "Refueling day; hunger likely due to cumulative training load. No damage to long-term progress."
  }
]


def main():
    # Get or create a default user
    user = User.objects.first()
    if not user:
        print("No user found. Creating a default user 'admin'...")
        user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("Created user 'admin' with password 'admin'")

    print(f"Importing data for user: {user.username}")

    dietary_count = 0
    exercise_count = 0

    for day in DATA:
        date = day['date']
        remarks = day.get('remarks', '')

        # Import food items
        for food in day.get('food', []):
            DietaryEntry.objects.create(
                user=user,
                date=date,
                item=food['item'],
                calories=food['calories'],
                notes=food.get('note', ''),
                remarks=remarks
            )
            dietary_count += 1

        # Import exercise entries
        for ex in day.get('exercise', []):
            ExerciseEntry.objects.create(
                user=user,
                date=date,
                activity=ex['activity'],
                duration_minutes=ex['duration_min'],
                calories_burned=ex.get('calories_burned'),
                remarks=remarks
            )
            exercise_count += 1

    print(f"\n✅ Import complete!")
    print(f"   - Dietary entries: {dietary_count}")
    print(f"   - Exercise entries: {exercise_count}")


if __name__ == '__main__':
    main()
