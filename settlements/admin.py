from django.contrib import admin

from settlements.models import Settlement


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ("date", "from_user", "to_user", "amount", "method", "status")
    list_filter = ("status", "method", "date")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("from_user", "to_user")
