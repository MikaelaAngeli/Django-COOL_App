# BudgetBuddy – Personal Expense Tracker

BudgetBuddy lets each registered user record, filter, and manage their own daily expenses. It uses Django, SQLite, Django templates, and Bootstrap 5.

## Features

- Register, log in, and log out.
- Add, view, edit, and delete expense and income transactions.
- Set a monthly budget and track spending progress, remaining budget, and over-budget status.
- Review monthly income, expenses, balance, and transaction counts.
- Search, filter, sort, and paginate transactions by type, category, payment method, date, and amount.
- View monthly category spending totals and a chart.
- Use expanded expense categories and separate GCash and Maya payment methods.
- Keep each user's budgets and transactions private to that user.
- Manage expenses, income, and budgets in Django admin.

## Setup (Windows PowerShell)

From the project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py makemigrations expenses
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Create a BudgetBuddy account, then add expenses. The admin site is at <http://127.0.0.1:8000/admin/>.

## Project layout

```text
Angeli_project/          Django project settings and root URLs
COOL_APP/                Expense model, forms, views, URLs, admin, tests
Templates/               Shared layout and app/auth HTML templates
manage.py
requirements.txt
```

The Django app package is `COOL_APP`. Its internal migration label remains `expenses` to preserve the existing SQLite tables and applied migration history. The HTML templates are stored in the top-level `Templates` folder and configured through `TEMPLATES[0]["DIRS"]` in `Angeli_project/settings.py`. The active timezone is Asia/Manila. The Bootstrap and Chart.js assets are loaded from CDNs.

## Notes

Bootstrap 5 CSS and JavaScript are loaded from jsDelivr, so a network connection is needed for the styling and responsive navigation. Before deploying, replace the development `SECRET_KEY`, disable `DEBUG`, configure `ALLOWED_HOSTS`, and use HTTPS.
