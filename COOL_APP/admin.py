from django.contrib import admin

from .models import Expense, Income, MonthlyBudget


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("amount", "category", "date", "payment_method", "user")
    list_filter = ("category", "date")
    search_fields = ("description",)


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("amount", "source", "date", "payment_method", "user")
    list_filter = ("source", "date")
    search_fields = ("description",)


@admin.register(MonthlyBudget)
class MonthlyBudgetAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "month", "amount")
    list_filter = ("year", "month")
