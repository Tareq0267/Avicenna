# Avicenna — Fitness Tracker (Django)

This is a minimal Django-based fitness tracker prototype that focuses on dietary, exercise and weight management tracking with a simple dashboard mock.

What you get in this scaffold
- Django project: `avicenna_project`
- App: `tracker` with models for dietary, exercise and weight entries
- Mock dashboard template at `/tracker/dashboard/`
- SQLite DB for quick local setup

Quick start (Windows / bash)

1. Create & activate a virtualenv (recommended)

```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash / WSL
# or: source .venv/bin/activate  # if using a unix-like shell
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run migrations

```bash
python manage.py migrate
```

4. Create a superuser (optional, to access admin)

```bash
python manage.py createsuperuser
```

5. Start the dev server

```bash
python manage.py runserver
```

6. Open the mock dashboard

Visit http://127.0.0.1:8000/tracker/dashboard/

Notes & next steps
- The scaffold uses SQLite for convenience. For production use, switch to Postgres or another DB.
- Add authentication restrictions to the dashboard as needed (it is left open in the mock).
- Small UI mock is provided with Bootstrap and a placeholder for charts.
