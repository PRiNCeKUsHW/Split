"""Move the shipped categories onto the current swatch palette.

The category editor offers a fixed set of colours so a new category cannot
break the visual system. The categories seeded in 0002 predate that palette,
so without this migration opening one in the editor and pressing save would
fail validation on a colour the user never touched.

Only rows still holding their original seeded colour are changed; anything
somebody has since recoloured by hand is left alone.
"""

from django.db import migrations

# name: (old seeded colour, new palette colour)
RECOLOUR = {
    "Rent": ("#3a34c9", "#a78bfa"),          # violet
    "Electricity": ("#e0a800", "#fdba74"),   # amber
    "WiFi": ("#0d6efd", "#67e8f9"),          # cyan
    "Maintenance": ("#6c757d", "#a3a3a3"),   # grey
    "Maid": ("#7048e8", "#f0abfc"),          # fuchsia
    "Groceries": ("#0b7a4b", "#bef264"),     # lime
    "Gas cylinder": ("#c42b4b", "#fb7185"),  # rose
    "One-off purchase": ("#495057", "#a3a3a3"),
}


def recolour(apps, schema_editor):
    Category = apps.get_model("expenses", "Category")
    for name, (old, new) in RECOLOUR.items():
        Category.objects.filter(name=name, color=old).update(color=new)


def restore(apps, schema_editor):
    Category = apps.get_model("expenses", "Category")
    for name, (old, new) in RECOLOUR.items():
        Category.objects.filter(name=name, color=new).update(color=old)


class Migration(migrations.Migration):
    dependencies = [("expenses", "0003_expense_source_template")]

    operations = [migrations.RunPython(recolour, restore)]
