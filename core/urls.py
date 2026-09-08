from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("balances/", views.BalancesView.as_view(), name="balances"),
    path("summary/", views.MonthlySummaryView.as_view(), name="summary"),
    path("summary/export/", views.MonthlyCSVView.as_view(), name="summary_csv"),
    path("close/", views.MonthCloseView.as_view(), name="month_close"),
    path("activity/", views.AuditLogView.as_view(), name="audit"),
]
