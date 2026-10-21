from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Expense(models.Model):
    class Category(models.TextChoices):
        FOOD = "Food", "Food"
        TRANSPORTATION = "Transportation", "Transportation"
        SCHOOL = "School", "School"
        HEALTH = "Health", "Health"
        BILLS = "Bills", "Bills"
        UTILITIES = "Utilities", "Utilities"
        PERSONAL_CARE = "Personal Care", "Personal care"
        SUBSCRIPTIONS = "Subscriptions", "Subscriptions"
        GIFTS = "Gifts", "Gifts"
        ENTERTAINMENT = "Entertainment", "Entertainment"
        SHOPPING = "Shopping", "Shopping"
        OTHER = "Other", "Other"

    class PaymentMethod(models.TextChoices):
        CASH = "Cash", "Cash"
        CREDIT_CARD = "Credit Card", "Credit Card"
        DEBIT_CARD = "Debit Card", "Debit Card"
        GCASH = "GCash", "GCash"
        MAYA = "Maya", "Maya"
        E_WALLET = "E-Wallet (GCash/Maya)", "E-Wallet (GCash/Maya)"
        BANK_TRANSFER = "Bank Transfer", "Bank Transfer"
        OTHER = "Other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    category = models.CharField(max_length=30, choices=Category.choices)
    description = models.TextField()
    date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices)

    class Meta:
        ordering = ["-date", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="expense_amount_positive"),
        ]

    def __str__(self):
        return f"{self.category} - {self.amount} on {self.date}"


class Income(models.Model):
    class Source(models.TextChoices):
        SALARY = "Salary", "Salary"
        ALLOWANCE = "Allowance", "Allowance"
        FREELANCE = "Freelance", "Freelance"
        BUSINESS = "Business", "Business"
        GIFT = "Gift", "Gift"
        OTHER = "Other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="income_records",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    source = models.CharField(max_length=20, choices=Source.choices)
    description = models.CharField(max_length=200)
    date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(
        max_length=30,
        choices=Expense.PaymentMethod.choices,
    )

    class Meta:
        ordering = ["-date", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="income_amount_positive"),
        ]

    def __str__(self):
        return f"{self.source} - {self.amount} on {self.date}"


class MonthlyBudget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="monthly_budgets",
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["user", "year", "month"], name="unique_user_monthly_budget"),
            models.CheckConstraint(condition=models.Q(month__gte=1, month__lte=12), name="budget_month_valid"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="budget_amount_positive"),
        ]

    def __str__(self):
        return f"{self.user} - {self.year}-{self.month:02d}: {self.amount}"
