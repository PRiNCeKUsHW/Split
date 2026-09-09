from django.urls import path

from expenses import views

app_name = "expenses"

urlpatterns = [
    path("", views.ExpenseListView.as_view(), name="list"),
    path("add/", views.ExpenseCreateView.as_view(), name="add"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_add"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
    path("preview/", views.SplitPreviewView.as_view(), name="preview"),
    path("<int:pk>/", views.ExpenseDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ExpenseUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ExpenseDeleteView.as_view(), name="delete"),
    path("<int:pk>/amount/", views.DraftAmountView.as_view(), name="draft_amount"),
    path("<int:pk>/comment/", views.CommentCreateView.as_view(), name="comment"),
]
