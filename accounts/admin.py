from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class FlatmateAdmin(UserAdmin):
    list_display = ("username", "display_name", "is_active_member", "joined_on", "left_on")
    list_filter = ("is_active_member", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Flatmate",
            {
                "fields": (
                    "display_name",
                    "phone",
                    "upi_id",
                    "avatar",
                    "is_active_member",
                    "joined_on",
                    "left_on",
                )
            },
        ),
    )


from accounts.models import AwayPeriod


@admin.register(AwayPeriod)
class AwayPeriodAdmin(admin.ModelAdmin):
    list_display = ("user", "start_date", "end_date", "days", "reason")
    list_filter = ("user",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")
