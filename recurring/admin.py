from django.contrib import admin

from recurring.models import RecurringExpense


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "category", "amount", "is_variable",
                    "day_of_month", "frequency", "is_active")
    list_filter = ("is_active", "is_variable", "frequency")
    filter_horizontal = ("default_participants",)
