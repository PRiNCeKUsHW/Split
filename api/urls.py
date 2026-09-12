from django.urls import path

from api import views

app_name = "api"

urlpatterns = [
    # Auth & Directory
    path("auth/login", views.auth_login, name="login"),
    path("auth/logout", views.auth_logout, name="logout"),
    path("auth/me", views.auth_me, name="me"),
    path("auth/profile", views.auth_profile_update, name="profile_update"),
    path("members", views.members_list, name="members"),
    path("members/create", views.member_create, name="member_create"),
    path("members/<int:pk>/edit", views.member_update, name="member_update"),
    path("categories", views.categories_list, name="categories"),

    # Dashboard
    path("dashboard", views.dashboard_view, name="dashboard"),

    # Expenses
    path("expenses", views.expense_list, name="expense_list"),
    path("expenses/create", views.expense_create, name="expense_create"),
    path("expenses/preview", views.expense_preview, name="expense_preview"),
    path("expenses/<int:pk>", views.expense_detail, name="expense_detail"),
    path("expenses/<int:pk>/edit", views.expense_update, name="expense_update"),
    path("expenses/<int:pk>/delete", views.expense_delete, name="expense_delete"),
    path("expenses/<int:pk>/amount", views.expense_fill_draft, name="expense_fill_draft"),
    path("expenses/<int:pk>/comment", views.expense_comment, name="expense_comment"),

    # Settlements
    path("settlements", views.settlements_overview, name="settlements_overview"),
    path("settlements/create", views.settlement_create, name="settlement_create"),
    path("settlements/<int:pk>/confirm", views.settlement_confirm, name="settlement_confirm"),
    path("settlements/<int:pk>/reject", views.settlement_reject, name="settlement_reject"),
    path("settlements/<int:pk>/qr", views.settlement_qr, name="settlement_qr"),

    # Recurring
    path("recurring", views.recurring_list, name="recurring_list"),
    path("recurring/generate", views.recurring_generate, name="recurring_generate"),

    # Away
    path("away", views.away_list, name="away_list"),
    path("away/create", views.away_create, name="away_create"),
    path("away/<int:pk>/delete", views.away_delete, name="away_delete"),

    # Activity
    path("activity", views.activity_list, name="activity_list"),

    # Summary (Flat Tab)
    path("summary", views.summary_view, name="summary_view"),
    path("month/toggle", views.month_toggle, name="month_toggle"),

    # Balances
    path("balances", views.balances_view, name="balances_view"),
]
