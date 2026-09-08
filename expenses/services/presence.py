"""Presence-day weighting.

Move-in/move-out proration and away-day proration are not two features. They
are one weight function with two switches:

    weight(u) = | days in [period_start, period_end]
                  intersect tenancy(u)
                  minus the union of u's away periods |

Both ends of every range are inclusive, everywhere, without exception.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Iterable, Sequence

DAY = dt.timedelta(days=1)


class AwayIndex:
    """Away periods for a set of people, loaded once.

    Built per split so that weighting N participants stays at one query
    rather than N.
    """

    def __init__(self, periods_by_user: dict[int, list[tuple[dt.date, dt.date]]]):
        self._by_user = periods_by_user

    @classmethod
    def for_users(
        cls, user_ids: Sequence[int], start: dt.date, end: dt.date
    ) -> "AwayIndex":
        from accounts.models import AwayPeriod

        rows = AwayPeriod.objects.filter(
            user_id__in=list(user_ids), start_date__lte=end, end_date__gte=start
        ).values_list("user_id", "start_date", "end_date")

        grouped: dict[int, list[tuple[dt.date, dt.date]]] = defaultdict(list)
        for user_id, first, last in rows:
            grouped[user_id].append((first, last))
        return cls(dict(grouped))

    @classmethod
    def empty(cls) -> "AwayIndex":
        return cls({})

    def away_days(self, user_id: int, start: dt.date, end: dt.date) -> int:
        """Days this person was away inside the window, counting each once."""
        return _union_days(self._by_user.get(user_id, ()), start, end)


def _union_days(
    intervals: Iterable[tuple[dt.date, dt.date]], start: dt.date, end: dt.date
) -> int:
    """Total days covered by the intervals within the window.

    Overlaps are counted once -- two trips booked over each other cannot
    subtract the same day twice.
    """
    clipped = sorted(
        (max(first, start), min(last, end))
        for first, last in intervals
        if first <= end and last >= start
    )
    if not clipped:
        return 0

    total = 0
    run_start, run_end = clipped[0]
    for first, last in clipped[1:]:
        if first > run_end + DAY:
            total += (run_end - run_start).days + 1
            run_start, run_end = first, last
        else:
            run_end = max(run_end, last)
    total += (run_end - run_start).days + 1
    return total


def presence_days(
    user,
    start: dt.date,
    end: dt.date,
    *,
    use_tenancy: bool,
    use_presence: bool,
    away_index: AwayIndex,
) -> int:
    """Days in [start, end] this person is chargeable for, both ends inclusive.

    ``use_tenancy`` clips the window to their move-in/move-out dates.
    ``use_presence`` additionally subtracts the days they were away.
    Clipping happens first, so a trip taken before someone moved in is not
    subtracted from days they were never charged for anyway.
    """
    window_start, window_end = start, end

    if use_tenancy:
        if user.joined_on:
            window_start = max(window_start, user.joined_on)
        if user.left_on:
            window_end = min(window_end, user.left_on)

    if window_end < window_start:
        return 0

    days = (window_end - window_start).days + 1
    if use_presence:
        days -= away_index.away_days(user.pk, window_start, window_end)

    return max(days, 0)


def weights_for(expense, participants: Sequence) -> dict[int, int] | None:
    """Presence weights for this expense, or None if it is not prorated.

    None means "no proration" and the caller should split evenly. Only EQUAL
    splits are ever prorated: the other three types are the user stating the
    answer explicitly, and second-guessing them would be wrong.
    """
    from expenses.models import Expense

    category = expense.category
    if expense.split_type != Expense.SplitType.EQUAL:
        return None
    if not (category.prorate_by_tenancy or category.prorate_by_presence):
        return None

    start = expense.period_start or expense.date
    end = expense.period_end or expense.date

    index = (
        AwayIndex.for_users([p.pk for p in participants], start, end)
        if category.prorate_by_presence
        else AwayIndex.empty()
    )

    return {
        person.pk: presence_days(
            person,
            start,
            end,
            use_tenancy=category.prorate_by_tenancy,
            use_presence=category.prorate_by_presence,
            away_index=index,
        )
        for person in participants
    }
