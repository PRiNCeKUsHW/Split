from django.urls import path

from settlements import views

app_name = "settlements"

urlpatterns = [
    path("", views.SettleUpView.as_view(), name="settle_up"),
    path("pay/<int:pk>/", views.RecordPaymentView.as_view(), name="record"),
    path("pending/", views.PendingConfirmationsView.as_view(), name="pending"),
    path("history/", views.SettlementHistoryView.as_view(), name="history"),
    path("<int:pk>/confirm/", views.ConfirmSettlementView.as_view(), name="confirm"),
    path("<int:pk>/reject/", views.RejectSettlementView.as_view(), name="reject"),
    path("qr/<int:pk>/", views.PaymentQRView.as_view(), name="qr"),
]
