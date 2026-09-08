"""The shipped categories must carry the proration flags from the design.

Getting these wrong is silent: rent would quietly discount people's holidays.
"""

import pytest

from expenses.models import Category

pytestmark = pytest.mark.django_db


def test_the_standard_categories_ship_with_the_app():
    names = set(Category.objects.values_list("name", flat=True))

    assert {
        "Rent", "Electricity", "WiFi", "Maintenance",
        "Groceries", "Gas cylinder", "Maid", "One-off purchase",
    } <= names


@pytest.mark.parametrize("name", ["Groceries", "Gas cylinder", "Maid"])
def test_shared_consumption_categories_prorate_by_away_days(name):
    category = Category.objects.get(name=name)

    assert category.prorate_by_presence is True
    assert category.prorate_by_tenancy is True


@pytest.mark.parametrize("name", ["Rent", "Electricity", "WiFi", "Maintenance"])
def test_housing_categories_ignore_away_days_but_respect_tenancy(name):
    """A holiday does not discount your rent. Moving out mid-month does."""
    category = Category.objects.get(name=name)

    assert category.prorate_by_presence is False
    assert category.prorate_by_tenancy is True


def test_a_one_off_purchase_is_never_prorated():
    category = Category.objects.get(name="One-off purchase")

    assert category.prorate_by_presence is False
    assert category.prorate_by_tenancy is False


def test_every_seeded_category_passes_its_own_validation():
    for category in Category.objects.all():
        category.full_clean()
