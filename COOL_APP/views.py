import calendar
from calendar import month_name
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import (
    BudgetBuddyAuthenticationForm,
    ExpenseForm,
    IncomeForm,
    MonthlyBudgetForm,
    RegistrationForm,
    TransactionFilterForm,
)
from .models import Expense, Income, MonthlyBudget


def _selected_period(request):
    today = timezone.localdate()
    requested_period = request.GET.get("month", "")
    try:
        period = date.fromisoformat(f"{requested_period}-01")
    except ValueError:
        period = today.replace(day=1)
    return period.replace(day=1)


def _period_navigation(period):
    previous = (period - timedelta(days=1)).replace(day=1)
    if period.month == 12:
        following = period.replace(year=period.year + 1, month=1)
    else:
        following = period.replace(month=period.month + 1)
    return previous, following


def _transaction_row(record, kind):
    if kind == "expense":
        label = record.get_category_display()
        detail_url = "expense_detail"
        edit_url = "expense_update"
        delete_url = "expense_delete"
    else:
        label = record.get_source_display()
        detail_url = "income_detail"
        edit_url = "income_update"
        delete_url = "income_delete"
    return {
        "record": record,
        "kind": kind,
        "label": label,
        "detail_url": detail_url,
        "edit_url": edit_url,
        "delete_url": delete_url,
    }


def _matching_transaction_rows(user, data=None, limit=None):
    expenses = Expense.objects.filter(user=user).select_related("user")
    incomes = Income.objects.filter(user=user).select_related("user")
    if data:
        search = data.get("q", "").strip()
        transaction_type = data.get("transaction_type", "")
        category = data.get("category", "")
        payment_method = data.get("payment_method", "")

        if transaction_type == "income":
            expenses = expenses.none()
        elif transaction_type == "expense":
            incomes = incomes.none()

        if category:
            expenses = expenses.filter(category=category)
            incomes = incomes.none()
        if payment_method:
            expenses = expenses.filter(payment_method=payment_method)
            incomes = incomes.filter(payment_method=payment_method)
        if data.get("date_from"):
            expenses = expenses.filter(date__gte=data["date_from"])
            incomes = incomes.filter(date__gte=data["date_from"])
        if data.get("date_to"):
            expenses = expenses.filter(date__lte=data["date_to"])
            incomes = incomes.filter(date__lte=data["date_to"])
        if data.get("min_amount") is not None:
            expenses = expenses.filter(amount__gte=data["min_amount"])
            incomes = incomes.filter(amount__gte=data["min_amount"])
        if data.get("max_amount") is not None:
            expenses = expenses.filter(amount__lte=data["max_amount"])
            incomes = incomes.filter(amount__lte=data["max_amount"])
        if search:
            expenses = expenses.filter(
                Q(description__icontains=search) | Q(category__icontains=search)
            )
            incomes = incomes.filter(
                Q(description__icontains=search) | Q(source__icontains=search)
            )

        sort = data.get("sort", "newest")
    else:
        sort = "newest"

    if limit and sort in ("newest", "oldest"):
        direction = "" if sort == "oldest" else "-"
        expenses = expenses.order_by(f"{direction}date", f"{direction}pk")[:limit]
        incomes = incomes.order_by(f"{direction}date", f"{direction}pk")[:limit]

    rows = [_transaction_row(item, "expense") for item in expenses]
    rows.extend(_transaction_row(item, "income") for item in incomes)
    reverse = sort not in ("oldest", "lowest")
    rows.sort(
        key=lambda row: (
            row["record"].date,
            row["record"].pk if row["kind"] == "expense" else row["record"].pk,
        ),
        reverse=reverse,
    )
    if sort in ("highest", "lowest"):
        rows.sort(
            key=lambda row: (row["record"].amount, row["record"].date, row["record"].pk),
            reverse=sort == "highest",
        )
    return rows


@login_required
def expense_list(request):
    today = timezone.localdate()
    period = _selected_period(request)
    previous, following = _period_navigation(period)
    quick_form = ExpenseForm(request.POST or None, prefix="quick")
    if request.method == "POST" and quick_form.is_valid():
        expense = quick_form.save(commit=False)
        expense.user = request.user
        expense.save()
        messages.success(request, "Expense added successfully.")
        return redirect("expense_list")

    user_expenses = Expense.objects.filter(user=request.user)
    monthly_expenses = Expense.objects.filter(
        user=request.user,
        date__year=period.year,
        date__month=period.month,
    )
    monthly_income = Income.objects.filter(
        user=request.user,
        date__year=period.year,
        date__month=period.month,
    )
    expense_total = monthly_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    income_total = monthly_income.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    budget = MonthlyBudget.objects.filter(
        user=request.user,
        year=period.year,
        month=period.month,
    ).first()
    budget_amount = budget.amount if budget else Decimal("0.00")
    percent_used = float(expense_total / budget_amount * 100) if budget_amount else 0
    recent_rows = _matching_transaction_rows(request.user, limit=6)
    category_totals = list(
        user_expenses.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    category_labels = dict(Expense.Category.choices)
    total_spent = user_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    for item in category_totals:
        item["label"] = category_labels[item["category"]]
        item["percentage"] = (
            float(item["total"] / total_spent * 100)
            if total_spent
            else 0
        )

    return render(
        request,
        "expenses/dashboard.html",
        {
            "period": period,
            "period_label": f"{month_name[period.month]} {period.year}",
            "current_month_label": f"{month_name[period.month]} {period.year}",
            "previous_month": previous.strftime("%Y-%m"),
            "next_month": following.strftime("%Y-%m"),
            "is_current_month": period.year == today.year and period.month == today.month,
            "expense_total": expense_total,
            "total_spent": total_spent,
            "income_total": income_total,
            "transaction_count": monthly_expenses.count() + monthly_income.count(),
            "all_expense_count": user_expenses.count(),
            "all_transaction_count": user_expenses.count() + Income.objects.filter(user=request.user).count(),
            "category_totals": category_totals,
            "top_category": category_totals[0] if category_totals else None,
            "balance": income_total - expense_total,
            "budget": budget,
            "budget_amount": budget_amount,
            "budget_remaining": budget_amount - expense_total,
            "percent_used": percent_used,
            "progress_width": min(percent_used, 100),
            "over_budget": bool(budget and expense_total > budget_amount),
            "budget_overage": max(expense_total - budget_amount, Decimal("0.00")),
            "recent_rows": recent_rows[:6],
            "quick_form": quick_form,
            "current_hour": timezone.localtime().hour,
            "dashboard_layout": True,
        },
    )


@login_required
def transaction_list(request):
    form = TransactionFilterForm(request.GET or None)
    rows = _matching_transaction_rows(request.user, form.cleaned_data if form.is_valid() else None)
    page_obj = Paginator(rows, 10).get_page(request.GET.get("page"))
    total_expenses = sum(
        (row["record"].amount for row in rows if row["kind"] == "expense"),
        Decimal("0.00"),
    )
    total_income = sum(
        (row["record"].amount for row in rows if row["kind"] == "income"),
        Decimal("0.00"),
    )
    return render(
        request,
        "expenses/transaction_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "rows": page_obj.object_list,
            "total_expenses": total_expenses,
            "total_income": total_income,
        },
    )


@login_required
def budget_update(request):
    period = _selected_period(request)
    today = timezone.localdate()
    previous, following = _period_navigation(period)
    budget = MonthlyBudget.objects.filter(
        user=request.user,
        year=period.year,
        month=period.month,
    ).first()
    daily_totals = {
        item["date"].day: item["total"]
        for item in Expense.objects.filter(
            user=request.user,
            date__year=period.year,
            date__month=period.month,
        )
        .values("date")
        .annotate(total=Sum("amount"))
    }
    month_calendar = calendar.Calendar(firstweekday=6)
    calendar_weeks = [
        [
            {
                "day": day,
                "amount": daily_totals.get(day, Decimal("0.00")),
                "has_expenses": day in daily_totals,
                "is_today": day == today.day and period.year == today.year and period.month == today.month,
                "date": f"{period.year:04d}-{period.month:02d}-{day:02d}" if day else "",
            }
            for day in week
        ]
        for week in month_calendar.monthdayscalendar(period.year, period.month)
    ]
    form = MonthlyBudgetForm(request.POST or None, instance=budget)
    if request.method == "POST" and form.is_valid():
        budget = form.save(commit=False)
        budget.user = request.user
        budget.year = period.year
        budget.month = period.month
        budget.save()
        messages.success(request, f"Budget for {month_name[period.month]} {period.year} saved.")
        return redirect(f"{reverse_lazy('expense_list')}?month={period:%Y-%m}")
    return render(
        request,
        "expenses/budget_form.html",
        {
            "form": form,
            "period": period,
            "period_label": f"{month_name[period.month]} {period.year}",
            "previous_month": previous.strftime("%Y-%m"),
            "next_month": following.strftime("%Y-%m"),
            "calendar_weeks": calendar_weeks,
        },
    )


@login_required
def profile(request):
    return render(request, "expenses/profile.html", {"dashboard_layout": True})


@login_required
def insights(request):
    period = _selected_period(request)
    previous, following = _period_navigation(period)
    category_totals = list(
        Expense.objects.filter(
            user=request.user,
            date__year=period.year,
            date__month=period.month,
        )
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    total = sum((item["total"] for item in category_totals), Decimal("0.00"))
    category_labels = dict(Expense.Category.choices)
    for item in category_totals:
        item["label"] = category_labels[item["category"]]
        item["percentage"] = float(item["total"] / total * 100) if total else 0
    return render(
        request,
        "expenses/insights.html",
        {
            "period": period,
            "period_label": f"{month_name[period.month]} {period.year}",
            "previous_month": previous.strftime("%Y-%m"),
            "next_month": following.strftime("%Y-%m"),
            "category_totals": category_totals,
            "total": total,
            "chart_labels": [item["label"] for item in category_totals],
            "chart_values": [float(item["total"]) for item in category_totals],
        },
    )


@login_required
def expense_detail(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    return render(request, "expenses/expense_detail.html", {"expense": expense})


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        expense.user = request.user
        expense.save()
        messages.success(request, "Expense added successfully.")
        return redirect("expense_detail", pk=expense.pk)
    return render(request, "expenses/expense_form.html", {"form": form, "title": "Add expense"})


@login_required
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    form = ExpenseForm(request.POST or None, instance=expense)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Expense updated successfully.")
        return redirect("expense_detail", pk=expense.pk)
    return render(request, "expenses/expense_form.html", {"form": form, "title": "Edit expense"})


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
        return redirect("expense_list")
    return render(request, "expenses/expense_confirm_delete.html", {"expense": expense})


@login_required
def income_detail(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    return render(request, "expenses/income_detail.html", {"income": income})


@login_required
def income_create(request):
    form = IncomeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        income = form.save(commit=False)
        income.user = request.user
        income.save()
        messages.success(request, "Income added successfully.")
        return redirect("income_detail", pk=income.pk)
    return render(request, "expenses/income_form.html", {"form": form, "title": "Add income"})


@login_required
def income_update(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    form = IncomeForm(request.POST or None, instance=income)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Income updated successfully.")
        return redirect("income_detail", pk=income.pk)
    return render(request, "expenses/income_form.html", {"form": form, "title": "Edit income"})


@login_required
def income_delete(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == "POST":
        income.delete()
        messages.success(request, "Income deleted successfully.")
        return redirect("transaction_list")
    return render(request, "expenses/income_confirm_delete.html", {"income": income})


class BudgetBuddyLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = BudgetBuddyAuthenticationForm


class BudgetBuddyLogoutView(LogoutView):
    next_page = reverse_lazy("login")


def register(request):
    if request.user.is_authenticated:
        return redirect("expense_list")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account was created successfully.")
        return redirect("expense_list")
    return render(request, "registration/register.html", {"form": form})
