from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Expense, Income, MonthlyBudget


def _add_bootstrap_classes(form):
    for field in form.fields.values():
        css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
        field.widget.attrs["class"] = css_class


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["amount", "category", "description", "date", "payment_method"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_bootstrap_classes(self)


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ["amount", "source", "description", "date", "payment_method"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_bootstrap_classes(self)


class MonthlyBudgetForm(forms.ModelForm):
    class Meta:
        model = MonthlyBudget
        fields = ["amount"]
        labels = {"amount": "Monthly budget (₱)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_bootstrap_classes(self)


class TransactionFilterForm(forms.Form):
    TRANSACTION_TYPES = (
        ("", "All transactions"),
        ("expense", "Expenses"),
        ("income", "Income"),
    )
    SORT_OPTIONS = (
        ("newest", "Newest"),
        ("oldest", "Oldest"),
        ("highest", "Highest amount"),
        ("lowest", "Lowest amount"),
    )

    q = forms.CharField(required=False, label="Search", widget=forms.TextInput(attrs={"placeholder": "Description"}))
    transaction_type = forms.ChoiceField(required=False, choices=TRANSACTION_TYPES, label="Type")
    category = forms.ChoiceField(required=False, label="Category")
    payment_method = forms.ChoiceField(required=False, label="Payment method")
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    min_amount = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=10, label="Min amount")
    max_amount = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=10, label="Max amount")
    sort = forms.ChoiceField(required=False, choices=SORT_OPTIONS, initial="newest")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [("", "All categories"), *Expense.Category.choices]
        self.fields["payment_method"].choices = [
            ("", "All payment methods"),
            *Expense.PaymentMethod.choices,
        ]
        _add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        min_amount = cleaned_data.get("min_amount")
        max_amount = cleaned_data.get("max_amount")
        if date_from and date_to and date_from > date_to:
            self.add_error("date_to", "End date must be on or after the start date.")
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            self.add_error("max_amount", "Maximum amount must be at least the minimum amount.")
        return cleaned_data


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_bootstrap_classes(self)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")


class BudgetBuddyAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_bootstrap_classes(self)
