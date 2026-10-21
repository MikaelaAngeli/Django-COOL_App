from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Expense, Income, MonthlyBudget


class ExpenseViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alex", password="test-password-123")
        self.other_user = User.objects.create_user(username="sam", password="test-password-123")
        self.expense = Expense.objects.create(
            user=self.user,
            amount=Decimal("12.50"),
            category=Expense.Category.FOOD,
            description="Lunch",
            payment_method=Expense.PaymentMethod.CASH,
        )
        self.income = Income.objects.create(
            user=self.user,
            amount=Decimal("50.00"),
            source=Income.Source.ALLOWANCE,
            description="Allowance",
            payment_method=Expense.PaymentMethod.GCASH,
        )

    def test_expense_pages_require_login(self):
        response = self.client.get(reverse("expense_list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('expense_list')}")

    def test_user_can_only_access_own_expenses(self):
        self.client.force_login(self.other_user)
        for name in ("expense_detail", "expense_update", "expense_delete"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=[self.expense.pk]))
                self.assertEqual(response.status_code, 404)
        for name in ("income_detail", "income_update", "income_delete"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=[self.income.pk]))
                self.assertEqual(response.status_code, 404)

    def test_create_assigns_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("expense_create"),
            {
                "amount": "8.25",
                "category": Expense.Category.SCHOOL,
                "description": "Notebook",
                "date": "2026-10-18",
                "payment_method": Expense.PaymentMethod.CASH,
            },
        )
        created = Expense.objects.get(description="Notebook")
        self.assertRedirects(response, reverse("expense_detail", args=[created.pk]))
        self.assertEqual(created.user, self.user)

    def test_dashboard_summarizes_monthly_budget_and_income(self):
        today = timezone.localdate()
        self.income.date = today
        self.income.amount = Decimal("100.00")
        self.income.save()
        MonthlyBudget.objects.create(
            user=self.user,
            amount=Decimal("20.00"),
            year=today.year,
            month=today.month,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("expense_list"))
        self.assertEqual(response.context["expense_total"], Decimal("12.50"))
        self.assertEqual(response.context["income_total"], Decimal("100.00"))
        self.assertEqual(response.context["balance"], Decimal("87.50"))
        self.assertEqual(response.context["budget_remaining"], Decimal("7.50"))
        self.assertContains(response, "Where your money goes")
        self.assertContains(response, "Add an expense")

    def test_dashboard_quick_add_creates_expense_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("expense_list"),
            {
                "quick-amount": "24.50",
                "quick-category": Expense.Category.SCHOOL,
                "quick-description": "Course materials",
                "quick-date": timezone.localdate().isoformat(),
                "quick-payment_method": Expense.PaymentMethod.GCASH,
            },
        )
        self.assertRedirects(response, reverse("expense_list"))
        created = Expense.objects.get(description="Course materials")
        self.assertEqual(created.user, self.user)

    def test_transaction_search_and_sort_are_user_scoped(self):
        Expense.objects.create(
            user=self.user,
            amount=Decimal("30.00"),
            category=Expense.Category.FOOD,
            description="Dinner out",
            payment_method=Expense.PaymentMethod.CASH,
        )
        Expense.objects.create(
            user=self.other_user,
            amount=Decimal("300.00"),
            category=Expense.Category.FOOD,
            description="Lunch secret",
            payment_method=Expense.PaymentMethod.CASH,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("transaction_list"),
            {"q": "food", "sort": "highest"},
        )
        self.assertEqual(response.context["total_expenses"], Decimal("42.50"))
        self.assertEqual(len(response.context["rows"]), 2)
        self.assertEqual(
            response.context["rows"][0]["record"].description,
            "Dinner out",
        )

    def test_budget_post_creates_budget_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("budget_update"), {"amount": "5000.00"})
        self.assertEqual(response.status_code, 302)
        today = timezone.localdate()
        budget = MonthlyBudget.objects.get(user=self.user, year=today.year, month=today.month)
        self.assertEqual(budget.amount, Decimal("5000.00"))
        self.assertFalse(MonthlyBudget.objects.filter(user=self.other_user).exists())

    def test_budget_tab_calendar_shows_monthly_daily_totals(self):
        self.client.force_login(self.user)
        target_month = timezone.localdate().replace(year=2026, month=2, day=1)
        Expense.objects.create(
            user=self.user,
            amount=Decimal("15.25"),
            category=Expense.Category.FOOD,
            description="Calendar lunch",
            date=target_month.replace(day=14),
            payment_method=Expense.PaymentMethod.CASH,
        )
        Expense.objects.create(
            user=self.other_user,
            amount=Decimal("200.00"),
            category=Expense.Category.FOOD,
            description="Private expense",
            date=target_month.replace(day=14),
            payment_method=Expense.PaymentMethod.CASH,
        )
        response = self.client.get(reverse("budget_update"), {"month": "2026-02"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["period"].strftime("%Y-%m"), "2026-02")
        calendar_days = [
            cell
            for week in response.context["calendar_weeks"]
            for cell in week
            if cell["day"] == 14
        ]
        self.assertEqual(len(calendar_days), 1)
        self.assertEqual(calendar_days[0]["amount"], Decimal("15.25"))
        self.assertTrue(calendar_days[0]["has_expenses"])
        self.assertContains(response, "₱15.25")
        self.assertContains(response, "2026-01")
        self.assertContains(response, "2026-03")

    def test_insights_show_category_spend(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("insights"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], Decimal("12.50"))
        self.assertEqual(response.context["category_totals"][0]["label"], "Food")
        self.assertContains(response, "Good to see you")

    def test_shared_dashboard_header_appears_on_other_tabs(self):
        self.client.force_login(self.user)
        for url_name in ("transaction_list", "insights", "budget_update"):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Personal finance")
                self.assertContains(response, "Good to see you")
                self.assertContains(response, "Monthly budget")

    def test_dark_theme_toggle_is_available_and_defaults_to_dark(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("expense_list"))
        self.assertContains(response, 'data-theme="dark"', html=False)
        self.assertContains(response, "budgetbuddy-theme")
        profile_response = self.client.get(reverse("profile"))
        self.assertContains(profile_response, "Switch to light mode")
        self.assertContains(profile_response, 'data-palette-picker', html=False)
        self.assertContains(profile_response, "Default Theme")
        self.assertContains(profile_response, "Ocean Pearl Delight")
        self.assertContains(profile_response, "Golden Twilight")
        self.assertContains(profile_response, "budgetbuddy-palette")
        self.client.logout()
        response = self.client.get(reverse("login"))
        self.assertNotContains(
            response,
            '<button class="btn btn-outline-light btn-sm ms-lg-2 theme-toggle"',
            html=False,
        )

    def test_profile_contains_theme_toggle_and_logout_action(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Appearance")
        self.assertContains(response, "data-theme-toggle")
        self.assertContains(response, reverse("logout"))

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_income_create_assigns_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("income_create"),
            {
                "amount": "450.00",
                "source": Income.Source.ALLOWANCE,
                "description": "Weekly allowance",
                "date": timezone.localdate().isoformat(),
                "payment_method": Expense.PaymentMethod.GCASH,
            },
        )
        income = Income.objects.get(description="Weekly allowance")
        self.assertRedirects(response, reverse("income_detail", args=[income.pk]))
        self.assertEqual(income.user, self.user)

    def test_non_positive_amount_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("expense_create"),
            {
                "amount": "0",
                "category": Expense.Category.FOOD,
                "description": "Invalid",
                "date": "2026-10-18",
                "payment_method": Expense.PaymentMethod.CASH,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Expense.objects.filter(description="Invalid").exists())

    def test_registration_creates_and_logs_in_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newstudent",
                "email": "student@example.com",
                "password1": "SecureTestPassword123!",
                "password2": "SecureTestPassword123!",
            },
        )
        self.assertRedirects(response, reverse("expense_list"))
        self.assertTrue(User.objects.filter(username="newstudent").exists())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_delete_requires_confirmation_post(self):
        self.client.force_login(self.user)
        confirmation = self.client.get(reverse("expense_delete", args=[self.expense.pk]))
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "Delete expense?")

        response = self.client.post(reverse("expense_delete", args=[self.expense.pk]))
        self.assertRedirects(response, reverse("expense_list"))
        self.assertFalse(Expense.objects.filter(pk=self.expense.pk).exists())
