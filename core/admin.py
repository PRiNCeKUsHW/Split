from django.contrib import admin

from core.models import AuditLog, MonthClose


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "model", "object_id", "label")
    list_filter = ("action", "model")
    readonly_fields = ("actor", "action", "model", "object_id", "label",
                       "changes", "created_at")

    def has_add_permission(self, request):
        return False  # written by services only

    def has_change_permission(self, request, obj=None):
        return False  # an editable audit log is not an audit log


@admin.register(MonthClose)
class MonthCloseAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "closed_by", "closed_at")
