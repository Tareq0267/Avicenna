# Avicenna - Fitness Tracker

## Project Overview

This is a Django-based fitness tracker application named Avicenna. It allows users to track their dietary intake, exercise, and weight. The project is built with Python and the Django web framework. It uses a SQLite database for local development.

The main features of the application are:

*   **Dashboard:** A central dashboard to view recent activities, summary statistics, and data visualizations.
*   **Dietary Tracking:** Log food intake and calories.
*   **Exercise Tracking:** Log physical activities and their duration.
*   **Weight Tracking:** Record weight over time.
*   **Couples Mode:** A feature that allows users to link with a partner and view their progress.
*   **AI Food Logging:** An experimental feature to log food using text or image analysis.
*   **Data Import:** Import activity data from a JSON file.

## Key Technologies

*   **Backend:** Python, Django
*   **Frontend:** HTML, CSS, JavaScript (with Bootstrap for styling and Chart.js for charts)
*   **Database:** SQLite (for development)
*   **Testing:** pytest, pytest-django

## Building and Running the Project

1.  **Create and activate a virtual environment:**

    ```bash
    python -m venv .venv
    source .venv/Scripts/activate
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Run database migrations:**

    ```bash
    python manage.py migrate
    ```

4.  **Create a superuser (optional, for admin access):**

    ```bash
    python manage.py createsuperuser
    ```

5.  **Start the development server:**

    ```bash
    python manage.py runserver
    ```

6.  **Access the application:**

    Open your web browser and go to `http://127.0.0.1:8000/tracker/dashboard/`.

## Development Conventions

*   The project follows the standard Django project structure.
*   The main application logic is contained within the `tracker` app.
*   Templates are stored in the `templates` directory.
*   Static files (CSS, JavaScript, images) are in the `static` directory.
*   Tests are written using `pytest` and `pytest-django` and are located in the `tests/` and `tracker/tests/` directories.
*   The project uses `python-dotenv` to manage environment variables. A `.env` file in the root directory is used to store sensitive information like the `SECRET_KEY`.
