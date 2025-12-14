# Avicenna Fitness Tracker - Test Suite

Comprehensive pytest test suite for the Avicenna fitness tracker application.

## Test Overview

| Module | Tests | Description |
|--------|-------|-------------|
| `test_models.py` | 21 | Model creation, relationships, cascade delete, string representations |
| `test_views.py` | 40 | Dashboard, import_json, add_weight, daily_recap views + URL routing |
| `test_admin.py` | 12 | Admin site registration and configuration |
| `test_management_commands.py` | 4 | `clear_data` management command |
| `test_templates.py` | 12 | Template content, inheritance, modals |
| `test_integration.py` | 18 | Full workflow and edge case tests |

**Total: 107 tests**

## Requirements

```bash
pip install pytest pytest-django
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

## Running Tests

### Run all tests
```bash
python -m pytest -v -p no:cov
```

### Run specific test file
```bash
python -m pytest tracker/tests/test_models.py -v -p no:cov
```

### Run specific test class
```bash
python -m pytest tracker/tests/test_views.py::TestDashboardView -v -p no:cov
```

### Run specific test
```bash
python -m pytest tracker/tests/test_views.py::TestDashboardView::test_dashboard_loads_successfully -v -p no:cov
```

### Run with shorter output
```bash
python -m pytest -p no:cov
```

## Test Categories

### Model Tests (`test_models.py`)
- **DietaryEntry**: Creation, string representation, blank fields, user relationships, cascade delete
- **ExerciseEntry**: Creation, nullable fields, user relationships, cascade delete
- **WeightEntry**: Creation, decimal precision, user relationships, cascade delete
- **Cross-model**: Multiple entry types on same date

### View Tests (`test_views.py`)
- **Dashboard**: Loading, template usage, context keys, empty/populated data states, chart data format
- **Import JSON**: POST validation, JSON parsing, field aliases (`food`/`dietary`, `note`/`notes`, `duration_min`/`duration_minutes`), remarks propagation
- **Add Weight**: POST validation, weight creation, date defaults
- **Daily Recap**: JSON response, summary calculations, date isolation
- **URL Routing**: All named URLs resolve correctly

### Admin Tests (`test_admin.py`)
- Model registration in admin site
- `list_display`, `list_filter`, `search_fields` configuration

### Management Command Tests (`test_management_commands.py`)
- `clear_data --force` functionality
- Empty database handling
- User preservation (only tracker data cleared)

### Template Tests (`test_templates.py`)
- Dashboard content (title, charts, heatmap, stat cards, recent entries)
- External libraries (ECharts, Bootstrap)
- Modal dialogs (import, weight, daily recap)
- Template inheritance

### Integration Tests (`test_integration.py`)
- **Workflows**: Import → Dashboard display, Add weight → Dashboard display, Import → Daily recap
- **Multi-day tracking**: Week of data, heatmap population
- **Data isolation**: Date filtering, user separation
- **Edge cases**: Large imports, multiple entries per day, zero calories, high values, decimal precision
- **Clear data**: Reset and fresh import

## Fixtures

Shared fixtures are defined in `conftest.py`:

| Fixture | Description |
|---------|-------------|
| `user` | Test user |
| `admin_user` | Admin user (used by import/add_weight views) |
| `dietary_entry` | Single dietary entry |
| `exercise_entry` | Single exercise entry |
| `weight_entry` | Single weight entry |
| `multiple_dietary_entries` | 7 dietary entries over 7 days |
| `multiple_exercise_entries` | 7 exercise entries over 7 days |
| `multiple_weight_entries` | 10 weight entries over 10 days |
| `sample_import_json` | Sample JSON data for import testing |
| `client` | Django test client |

## Configuration

Test configuration is in `pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = avicenna_project.settings
python_files = tests.py test_*.py *_test.py
addopts = -v --tb=short
```

## Notes

- Tests use an in-memory SQLite database (isolated from your dev database)
- The `-p no:cov` flag disables the coverage plugin if installed (avoids potential conflicts)
- All tests are independent and can run in any order
