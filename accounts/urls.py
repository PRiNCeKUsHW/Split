from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.FlatLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("members/", views.MemberListView.as_view(), name="members"),
    path("members/add/", views.InviteFlatmateView.as_view(), name="invite"),
    path("members/<int:pk>/edit/", views.MemberUpdateView.as_view(), name="member_edit"),
    path(
        "set-password/<uidb64>/<token>/",
        views.SetPasswordView.as_view(),
        name="set_password",
    ),
]

urlpatterns += [
    path("away/", views.AwayPeriodListView.as_view(), name="away"),
    path("away/add/", views.AwayPeriodCreateView.as_view(), name="away_add"),
    path("away/<int:pk>/delete/", views.AwayPeriodDeleteView.as_view(), name="away_delete"),
]
