"""Pre-built routine templates that users can add with one click."""

ROUTINE_PRESETS = {
    'solat_subuh': {
        'name': 'Solat Subuh',
        'description': 'Fajr prayer',
        'schedule_type': 'daily',
        'schedule_config': {'time': '05:30'},

        'icon': 'bi-moon-stars',
        'color': '#818cf8',
        'group': 'solat',
    },
    'solat_zohor': {
        'name': 'Solat Zohor',
        'description': 'Dhuhr prayer',
        'schedule_type': 'daily',
        'schedule_config': {'time': '13:00'},

        'icon': 'bi-sun',
        'color': '#facc15',
        'group': 'solat',
    },
    'solat_asar': {
        'name': 'Solat Asar',
        'description': 'Asr prayer',
        'schedule_type': 'daily',
        'schedule_config': {'time': '16:30'},

        'icon': 'bi-cloud-sun',
        'color': '#fb923c',
        'group': 'solat',
    },
    'solat_maghrib': {
        'name': 'Solat Maghrib',
        'description': 'Maghrib prayer',
        'schedule_type': 'daily',
        'schedule_config': {'time': '19:15'},

        'icon': 'bi-sunset',
        'color': '#f87171',
        'group': 'solat',
    },
    'solat_isyak': {
        'name': 'Solat Isyak',
        'description': 'Isha prayer',
        'schedule_type': 'daily',
        'schedule_config': {'time': '20:30'},

        'icon': 'bi-moon',
        'color': '#a78bfa',
        'group': 'solat',
    },
    'exercise_morning': {
        'name': 'Morning Exercise',
        'description': '30 min workout',
        'schedule_type': 'daily',
        'schedule_config': {'time': '07:00'},

        'icon': 'bi-lightning-charge',
        'color': '#34d399',
        'group': 'health',
    },
    'shower_morning': {
        'name': 'Morning Shower',
        'description': 'Morning hygiene routine',
        'schedule_type': 'daily',
        'schedule_config': {'time': '06:30'},

        'icon': 'bi-droplet',
        'color': '#38bdf8',
        'group': 'health',
    },
    'drink_water': {
        'name': 'Drink 8 Glasses of Water',
        'description': 'Stay hydrated throughout the day',
        'schedule_type': 'daily',
        'schedule_config': {},

        'icon': 'bi-cup-straw',
        'color': '#2dd4bf',
        'group': 'health',
    },
    'read_quran': {
        'name': 'Read Quran',
        'description': 'Daily Quran reading',
        'schedule_type': 'daily',
        'schedule_config': {},

        'icon': 'bi-book',
        'color': '#34d399',
        'group': 'spiritual',
    },
    'skincare': {
        'name': 'Skincare Routine',
        'description': 'Morning/night skincare',
        'schedule_type': 'daily',
        'schedule_config': {},

        'icon': 'bi-stars',
        'color': '#f472b6',
        'group': 'health',
    },
}

# Group metadata for display
PRESET_GROUPS = {
    'solat': {
        'name': 'Solat (5 Daily Prayers)',
        'icon': 'bi-moon-stars',
        'color': '#818cf8',
    },
    'health': {
        'name': 'Health & Hygiene',
        'icon': 'bi-heart-pulse',
        'color': '#34d399',
    },
    'spiritual': {
        'name': 'Spiritual',
        'icon': 'bi-book',
        'color': '#34d399',
    },
}


def get_presets_by_group():
    """Return presets organized by group."""
    grouped = {}
    for key, preset in ROUTINE_PRESETS.items():
        group = preset['group']
        if group not in grouped:
            grouped[group] = {
                'meta': PRESET_GROUPS.get(group, {'name': group.title(), 'icon': 'bi-collection', 'color': '#6b7280'}),
                'presets': [],
            }
        grouped[group]['presets'].append({'key': key, **preset})
    return grouped


def add_preset_for_user(user, preset_key):
    """Create a Routine from a preset for the given user. Returns the Routine or None."""
    from .models import Routine
    preset = ROUTINE_PRESETS.get(preset_key)
    if not preset:
        return None
    # Don't add duplicate presets
    if Routine.objects.filter(user=user, preset_key=preset_key, is_active=True).exists():
        return None
    return Routine.objects.create(
        user=user,
        name=preset['name'],
        description=preset['description'],
        schedule_type=preset['schedule_type'],
        schedule_config=preset['schedule_config'],
        preset_key=preset_key,
        icon=preset['icon'],
        color=preset['color'],
    )


def add_preset_group_for_user(user, group_name):
    """Add all presets in a group for the user. Returns list of created Routines."""
    created = []
    for key, preset in ROUTINE_PRESETS.items():
        if preset['group'] == group_name:
            routine = add_preset_for_user(user, key)
            if routine:
                created.append(routine)
    return created
