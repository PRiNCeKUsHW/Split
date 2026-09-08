from django.contrib import admin

from expenses.models import Category, Comment, Expense, ExpenseShare


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "prorate_by_tenancy", "prorate_by_presence",
                    "is_recurring_by_default", "sort_order")
    list_editable = ("prorate_by_tenancy", "prorate_by_presence")
    ordering = ("sort_order", "name")


class ExpenseShareInline(admin.TabularInline):
    model = ExpenseShare
    extra = 0
    readonly_fields = ("amount_owed", "share_units", "percent", "present_days")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Shares are derived. Editing them by hand would desync the total.
        return False


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "amount", "category", "paid_by",
                    "split_type", "is_draft", "is_deleted")
    list_filter = ("category", "split_type", "is_draft", "is_deleted", "date")
    search_fields = ("description", "notes")
    date_hierarchy = "date"
    inlines = [ExpenseShareInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category", "paid_by")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("expense", "author", "created_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("expense", "author")
