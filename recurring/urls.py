from django.urls import path

from recurring import views

app_name = "recurring"

urlpatterns = [
    path("", views.RecurringListView.as_view(), name="list"),
    path("add/", views.RecurringCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.RecurringUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.RecurringDeleteView.as_view(), name="delete"),
    path("generate/", views.GenerateNowView.as_view(), name="generate"),
]
