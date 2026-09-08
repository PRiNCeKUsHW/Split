"""Ship the categories a shared flat actually has, with the right proration.

The two flags are the whole point of this migration. `prorate_by_presence`
discounts the days someone was away — right for food, gas and the maid, wrong
for rent, where an empty room still costs what it costs.
"""

from django.db import migrations

# name, icon, colour, recurring by default, tenancy, presence, sort order
CATEGORIES = [
    ("Rent", "house", "#3a34c9", True, True, False, 10),
    ("Electricity", "bolt", "#e0a800", True, True, False, 20),
    ("WiFi", "wifi", "#0d6efd", True, True, False, 30),
    ("Maintenance", "tools", "#6c757d", True, True, False, 40),
    ("Maid", "broom", "#7048e8", True, True, True, 50),
    ("Groceries", "basket", "#0b7a4b", False, True, True, 60),
    ("Gas cylinder", "flame", "#c42b4b", False, True, True, 70),
    ("One-off purchase", "tag", "#495057", False, False, False, 80),
]


def seed(apps, schema_editor):
    Category = apps.get_model("expenses", "Category")
    for name, icon, color, recurring, tenancy, presence, order in CATEGORIES:
        Category.objects.update_or_create(
            name=name,
            defaults={
                "icon": icon,
                "color": color,
                "is_recurring_by_default": recurring,
                "prorate_by_tenancy": tenancy,
                "prorate_by_presence": presence,
                "sort_order": order,
            },
        )


def unseed(apps, schema_editor):
    """Only remove categories nobody has used, so history survives a rollback."""
    Category = apps.get_model("expenses", "Category")
    names = [row[0] for row in CATEGORIES]
    Category.objects.filter(name__in=names, expenses__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("expenses", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
