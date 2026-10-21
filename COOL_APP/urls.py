from django.urls import path

from . import views

urlpatterns = [
    path("", views.expense_list, name="expense_list"),
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("insights/", views.insights, name="insights"),
    path("budget/", views.budget_update, name="budget_update"),
    path("profile/", views.profile, name="profile"),
    path("expense/add/", views.expense_create, name="expense_create"),
    path("expense/<int:pk>/", views.expense_detail, name="expense_detail"),
    path("expense/<int:pk>/edit/", views.expense_update, name="expense_update"),
    path("expense/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
    path("income/add/", views.income_create, name="income_create"),
    path("income/<int:pk>/", views.income_detail, name="income_detail"),
    path("income/<int:pk>/edit/", views.income_update, name="income_update"),
    path("income/<int:pk>/delete/", views.income_delete, name="income_delete"),
    path("register/", views.register, name="register"),
    path("login/", views.BudgetBuddyLoginView.as_view(), name="login"),
    path("logout/", views.BudgetBuddyLogoutView.as_view(), name="logout"),
]
