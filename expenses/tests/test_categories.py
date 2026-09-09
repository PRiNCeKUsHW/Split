"""User-managed categories.

The whole point of the behaviour picker is that the invalid combination —
away-day proration without tenancy proration — is unreachable, not merely
rejected. These tests hold that line.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from expenses.forms import CategoryForm
from expenses.models import Category

pytestmark = pytest.mark.django_db


@pytest.fixture
def logged_in(client, anuj):
    client.force_login(anuj)
    return client


def _data(**overrides):
    data = {"name": "Milk delivery", "behaviour": "PRESENCE", "color": "#bef264",
            "icon": "basket"}
    data.update(overrides)
    return data


# -------------------------------------------------------- behaviour mapping


@pytest.mark.parametrize(
    "behaviour,tenancy,presence",
    [
        ("EVEN", False, False),
        ("TENANCY", True, False),
        ("PRESENCE", True, True),
    ],
)
def test_behaviour_maps_onto_the_two_flags(behaviour, tenancy, presence):
    form = CategoryForm(_data(behaviour=behaviour))

    assert form.is_valid(), form.errors
    category = form.save()

    assert category.prorate_by_tenancy is tenancy
    assert category.prorate_by_presence is presence


def test_the_invalid_combination_cannot_be_expressed():
    """There is no behaviour that yields presence-without-tenancy."""
    produced = set()
    for behaviour in ("EVEN", "TENANCY", "PRESENCE"):
        form = CategoryForm(_data(name=f"C {behaviour}", behaviour=behaviour))
        assert form.is_valid(), form.errors
        category = form.save()
        produced.add((category.prorate_by_tenancy, category.prorate_by_presence))

    assert (False, True) not in produced


def test_an_unknown_behaviour_is_rejected():
    form = CategoryForm(_data(behaviour="WHATEVER"))

    assert not form.is_valid()
    assert "behaviour" in form.errors


def test_editing_starts_from_the_categorys_current_behaviour(groceries):
    form = CategoryForm(instance=groceries)

    assert form.initial["behaviour"] == "PRESENCE"


def test_editing_rent_shows_tenancy_not_presence(rent):
    assert CategoryForm(instance=rent).initial["behaviour"] == "TENANCY"


def test_editing_a_plain_category_shows_even(one_off):
    assert CategoryForm(instance=one_off).initial["behaviour"] == "EVEN"


def test_the_behaviour_survives_a_round_trip(groceries):
    form = CategoryForm(_data(name=groceries.name, behaviour="PRESENCE"),
                        instance=groceries)
    assert form.is_valid(), form.errors
    form.save()

    groceries.refresh_from_db()
    assert CategoryForm(instance=groceries).initial["behaviour"] == "PRESENCE"


def test_the_model_reports_its_own_behaviour(groceries, rent, one_off):
    assert groceries.behaviour == "PRESENCE"
    assert rent.behaviour == "TENANCY"
    assert one_off.behaviour == "EVEN"


# ------------------------------------------------------------- validation


def test_a_duplicate_name_is_rejected(groceries):
    form = CategoryForm(_data(name="Groceries"))

    assert not form.is_valid()
    assert "name" in form.errors


def test_a_colour_outside_the_palette_is_rejected():
    """A free hex field would let a custom category break the visual system."""
    form = CategoryForm(_data(color="#ff00ff"))

    assert not form.is_valid()
    assert "color" in form.errors


def test_every_offered_colour_is_accepted():
    for index, (value, _label) in enumerate(CategoryForm.COLOURS):
        form = CategoryForm(_data(name=f"Cat {index}", color=value))
        assert form.is_valid(), f"{value} was rejected: {form.errors}"


# ------------------------------------------------------------------ views


def test_any_flatmate_can_see_the_category_list(logged_in):
    response = logged_in.get(reverse("expenses:category_list"))

    assert response.status_code == 200
    assert b"Groceries" in response.content


def test_any_flatmate_can_create_a_category(logged_in):
    response = logged_in.post(reverse("expenses:category_add"), _data())

    assert response.status_code == 302
    assert Category.objects.filter(name="Milk delivery").exists()


def test_a_created_category_prorates_as_chosen(logged_in):
    logged_in.post(reverse("expenses:category_add"), _data(behaviour="PRESENCE"))

    category = Category.objects.get(name="Milk delivery")
    assert category.prorate_by_presence is True
    assert category.prorate_by_tenancy is True


def test_a_new_category_can_be_used_on_an_expense(logged_in, anuj, priya):
    logged_in.post(reverse("expenses:category_add"), _data(behaviour="EVEN"))
    category = Category.objects.get(name="Milk delivery")

    response = logged_in.post(
        reverse("expenses:add"),
        {
            "amount": "300.00", "description": "Milk for the week",
            "category": category.pk, "paid_by": anuj.pk, "date": "2026-09-15",
            "split_type": "EQUAL", "participants": [anuj.pk, priya.pk], "notes": "",
        },
    )

    assert response.status_code == 302
    from expenses.models import Expense

    expense = Expense.objects.get(description="Milk for the week")
    assert expense.shares_total == Decimal("300.00")


def test_a_flatmate_can_rename_a_category(logged_in, one_off):
    logged_in.post(
        reverse("expenses:category_edit", args=[one_off.pk]),
        _data(name="Odds and ends", behaviour="EVEN"),
    )

    one_off.refresh_from_db()
    assert one_off.name == "Odds and ends"


def test_an_unused_category_can_be_deleted(logged_in, one_off):
    response = logged_in.post(reverse("expenses:category_delete", args=[one_off.pk]))

    assert response.status_code == 302
    assert not Category.objects.filter(pk=one_off.pk).exists()


def test_a_category_in_use_cannot_be_deleted(logged_in, groceries, anuj, make_expense):
    make_expense(category=groceries, paid_by=anuj, amount="100.00")

    response = logged_in.post(
        reverse("expenses:category_delete", args=[groceries.pk]), follow=True
    )

    assert Category.objects.filter(pk=groceries.pk).exists()
    assert b"1 expense" in response.content


def test_the_refusal_names_how_many_expenses_are_blocking(
    logged_in, groceries, anuj, make_expense
):
    for index in range(3):
        make_expense(category=groceries, paid_by=anuj, amount="10.00",
                     description=f"Shop {index}")

    response = logged_in.post(
        reverse("expenses:category_delete", args=[groceries.pk]), follow=True
    )

    assert b"3 expenses" in response.content


def test_a_category_used_only_by_a_recurring_template_cannot_be_deleted(
    logged_in, one_off, anuj
):
    from recurring.models import RecurringExpense

    RecurringExpense.objects.create(
        description="Newspaper", category=one_off, amount=Decimal("300.00"),
        paid_by=anuj,
    )

    logged_in.post(reverse("expenses:category_delete", args=[one_off.pk]), follow=True)

    assert Category.objects.filter(pk=one_off.pk).exists()


def test_the_category_screens_need_a_login(client, groceries):
    for name, args in [
        ("expenses:category_list", []),
        ("expenses:category_add", []),
        ("expenses:category_edit", [groceries.pk]),
    ]:
        response = client.get(reverse(name, args=args))
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]


def test_a_shipped_category_can_be_edited_without_touching_its_colour(
    logged_in, rent
):
    """The real path: open Rent, change the name, save.

    If a seeded colour is not one of the offered swatches, the form comes
    back invalid on a field the user never touched.
    """
    form = CategoryForm(instance=rent)
    current = form.initial.get("color", rent.color)

    response = logged_in.post(
        reverse("expenses:category_edit", args=[rent.pk]),
        {"name": "House rent", "behaviour": "TENANCY", "color": current, "icon": rent.icon},
    )

    assert response.status_code == 302, "editing a shipped category was rejected"
    rent.refresh_from_db()
    assert rent.name == "House rent"


def test_every_shipped_category_uses_a_colour_from_the_palette():
    offered = {value for value, _ in CategoryForm.COLOURS}

    for category in Category.objects.all():
        assert category.color in offered, (
            f"{category.name} ships with {category.color}, which is not a swatch"
        )
