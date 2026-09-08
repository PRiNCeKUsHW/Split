# FlatSplit — Design

Self-hosted Django expense splitter for a shared flat. LAN-only, phone-first, offline-capable.
This document records the **decisions and algorithms**; the feature brief supplied by the
project owner remains the source of truth for screens, models, and phase order.

## Decisions locked (2026-09-08)

| # | Question | Decision |
|---|----------|----------|
| 1 | AwayPeriod endpoint semantics | **Both ends inclusive.** 5–8 Sept = 4 days not paid for. |
| 2 | Does travel reduce rent? | **No.** Two independent category flags; tenancy always gates, presence is opt-in. |
| 3 | Leftover paise | **Largest fractional remainder**, ties broken payer-first, then `user.id`. |
| 4 | Zero-presence participant | **Keep a ₹0.00 share row.** If every weight is 0, fall back to flat equal. |

---

## 1. The presence-day model

Move-in/move-out proration and away-days proration are not two features. They are one
weight function with two switches. Everything prorated funnels through it.

### Category flags

`Category` carries two booleans instead of the single flag in the brief:

| Category | `prorate_by_tenancy` | `prorate_by_presence` |
|---|---|---|
| Rent | ✓ | ✗ |
| Electricity, WiFi, Maintenance | ✓ | ✗ |
| Groceries, Gas cylinder, Maid | ✓ | ✓ |
| One-off purchase | ✗ | ✗ |

`prorate_by_presence` implies `prorate_by_tenancy` — enforced in `Category.clean()`.
You cannot owe for days before you moved in, under any flag combination.

### Weight function

```python
def presence_days(
    user: User,
    start: date,
    end: date,
    *,
    use_tenancy: bool,
    use_presence: bool,
    away_index: AwayIndex,
) -> int:
    """Number of days in [start, end] this user is chargeable for. Both ends inclusive."""
```

- The window is `[period_start, period_end]`, **inclusive both ends**. When the expense has
  no period, both collapse to `expense.date` → a one-day window.
- `use_tenancy` clips the window to `[joined_on, left_on or +inf]`.
- `use_presence` subtracts the **union** of that user's `AwayPeriod` rows overlapping the
  window. Union, never sum — two overlapping trips cannot drive a weight below zero.
- Weights are computed over **selected participants only**. The picker still decides who is in.
- Proration applies to `EQUAL` only. `EXACT`, `PERCENT` and `SHARES` are the user overriding
  the machine; never second-guess them.

`AwayIndex` is a small prefetch helper built once per split (one query for all participants'
away periods), so splitting N participants stays at O(1) queries.

### Edge cases

| Situation | Behaviour |
|---|---|
| No `period_start` / `period_end` | Single-day window at `expense.date`. |
| Participant away the whole window | Weight 0 → ₹0.00 share row, still listed. |
| Participant not yet moved in | Weight 0 → ₹0.00 share row. |
| **All** weights 0 | Fall back to flat equal (1 each) rather than divide by zero. |
| `period_end` earlier than `period_start` | Form validation error. |
| Overlapping away periods | Deduplicated by union. |
| Away period straddling the window edge | Clipped to the window. |

Worked: **₹3000 groceries, 1–30 Sept, C away 10 days** → weights 30/30/20 → ₹1125 / ₹1125 / ₹750.

Worked: **₹30000 rent, Sept, D moved in on the 11th** → weights 30/30/30/20 → ₹8181.82 ×3, ₹5454.54.

---

## 2. Rounding and remainder allocation

Integer paise end to end. `Decimal` appears only at the boundaries — parsing input and
writing `DecimalField`. No `float` anywhere in the money path; a test greps for it.

```python
def allocate(total_paise: int, weights: Sequence[int], tie_break: Sequence[int]) -> list[int]:
    """Split total_paise proportionally to weights. Sum of result == total_paise, exactly."""
```

1. `share_i = (total_paise * weight_i) // total_weight` — floor, so the sum never overshoots.
2. `remainder = total_paise - sum(shares)`, guaranteed to be at least 0 and less than the
   number of participants.
3. Sort recipients by `(-fractional_part, tie_break_rank)` and give one paise to the first
   `remainder` of them. `tie_break_rank` is 0 for the payer, then `user.id` ascending.
4. `assert sum(shares) == total_paise` inside the service — the invariant is enforced in
   code, not merely tested.

On a plain equal split every fractional part is identical, so step 3 collapses to
"the payer absorbs it", exactly as the brief asked.

| Input | Result |
|---|---|
| ₹100 ÷ 3 equal | ₹33.34 (payer), ₹33.33, ₹33.33 |
| ₹0.05 ÷ 3 | ₹0.02, ₹0.02, ₹0.01 |
| ₹1000 ÷ 7 | ₹142.86 ×5, ₹142.85 ×2 |
| ₹100 shares 2:1:1 | ₹50.00, ₹25.00, ₹25.00 (no remainder) |
| ₹1000, weights 30/30/25 | ₹352.94, ₹352.94, ₹294.12 — C rounded down hardest, C gets the paise |

`EXACT` bypasses allocation entirely; the form validates the sum equals the total.
`PERCENT` validates the sum equals 100, then allocates on percent-as-weight.

### Invariants under test

- Every `ExpenseShare` set sums to `expense.amount` exactly, for all four split types.
- Property test: random amounts × random weights × 2–8 participants → sum always exact.
- Recomputing a split is idempotent — same input, byte-identical shares.
- Balances across all users sum to exactly zero.
- `simplify_debts` output fully settles every balance and its amounts net to zero.

---

## 3. Service boundaries

Fat services, thin views, thin models. Every function below is importable and testable
without a request, a session, or the ORM where practical.

```
expenses/services/presence.py     presence_days, AwayIndex, build_weights
expenses/services/split.py        allocate, build_shares, recompute_shares
settlements/services/balances.py  get_balances, get_month_totals
settlements/services/simplify.py  simplify_debts
recurring/services.py             generate_for_month  (idempotent)
core/services/audit.py            record(actor, action, instance, changes)
core/services/monthclose.py       is_month_closed, assert_open
```

`split.build_shares` takes plain data (total, participant ids, weights, payer id) and returns
plain results. The model-writing wrapper is separate, so the math tests never touch a database.

---

## 4. Deltas from the brief

Additions the brief implies but does not name. Flagging them rather than smuggling them in:

- **`Category.prorate_by_tenancy`** alongside `prorate_by_presence` — decision 2.
- **`ExpenseShare.present_days`** (nullable int) next to `share_units` and `percent`, so the
  detail screen can show *why* a share is what it is: "Rohit · 20 of 80 days".
- **`Expense.amount` nullable + `is_draft`** — required by variable recurring bills. Shares
  are only generated once an amount exists; drafts are excluded from balances.
- **`expenses.Comment`** — the brief specifies a comment thread on expense detail but lists
  no model.
- **`Expense.period_start` / `period_end`** default to `date` on save when left blank, so
  downstream code never branches on null.

---

## 5. Balances

`get_balances()` returns net position per active member:

```
net(u) = sum(expenses u paid, non-draft, not deleted)
       - sum(u's shares)
       + sum(confirmed settlements u sent)
       - sum(confirmed settlements u received)
```

**Correction (2026-09-08, during phase 4):** an earlier revision of this
document had the settlement signs reversed. Paying someone back reduces what
you owe, so a *sent* settlement moves your balance **up**; receiving one moves
it **down**. Worked check: A pays ₹100 split evenly, so A is +50 and B is −50.
B then settles ₹50 to A. B: `0 − 50 + 50 = 0`. A: `100 − 50 − 50 = 0`. Both
land on zero, as they must. The reversed version drove B to −100.

`PENDING` and `REJECTED` settlements are invisible to balances. Summed in paise, converted
to `Decimal` once at the end. `simplify_debts` is greedy largest-creditor / largest-debtor,
also in paise, so no drift can accumulate across a chain of transfers.

---

## 6. Build phases

Each phase stops for review. Exit criterion is "tests green", stated per phase.

| # | Phase | Exit criterion |
|---|---|---|
| 1 | Scaffold, settings split, custom User, auth, base template, vendored CSS, WhiteNoise, PWA | `pytest` green; app loads styled with WiFi off; login works |
| 2 | Category / Expense / ExpenseShare + split engine | Full split-type and rounding suite green, including the property test |
| 3 | Add-expense, list, detail with HTMX | View tests plus `assertNumQueries` on the list |
| 4 | Balances, debt simplification, dashboard | Settle-to-zero and sums-to-zero suites green |
| 5 | Settlements, confirm flow, UPI link, QR | Pending settlement provably does not move balances |
| 6 | Recurring plus `generate_recurring` | Running the command twice creates nothing the second time |
| 7 | Away periods, presence and tenancy proration | Edge-case table above, each row a test |
| 8 | Audit log, month close, monthly summary, CSV | Closed-month write rejected at the form layer, not just hidden in the UI |
| 9 | Receipts, polish, `run.sh`, README, `seed_demo` | Fresh clone → seeded, styled, usable app on a phone |

QR generation uses `qrcode[pil]`, rendered server-side to an inline data URI — no CDN, no JS
library, consistent with the offline constraint.
