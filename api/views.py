from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from accounts.models import AwayPeriod
from core.models import AuditLog, MonthClose
from core.services.audit import record_create, record_update
from core.services.monthclose import assert_open, close_month, is_closed, reopen_month
from expenses.forms import ExpenseForm
from expenses.models import Category, Comment, Expense, ExpenseShare
from expenses.services.crud import (
    create_expense,
    delete_expense,
    fill_draft_amount,
    update_expense,
)
from expenses.services.presence import weights_for
from expenses.services.shares import rebuild_shares
from expenses.services.split import SplitError, SplitType, allocate, compute_shares
from recurring.models import RecurringExpense
from recurring.services import drafts_needing_amounts, generate_for_month
from settlements.models import Settlement
from settlements.services.balances import (
    get_balance_for,
    get_balance_rows,
    get_balances,
)
from settlements.services.simplify import simplify_debts
from django.contrib.auth.decorators import login_not_required
from settlements.services.upi import payment_qr, upi_link

User = get_user_model()
ZERO = Decimal("0.00")


def json_auth_required(view_func):
    @login_not_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required", "authenticated": False}, status=401)
        return view_func(request, *args, **kwargs)

    return _wrapped


def _serialize_user(user: User | None) -> dict:
    if not user:
        return {
            "id": 0,
            "username": "",
            "name": "Flatmate",
            "display_name": "Flatmate",
            "upi_id": "",
            "initials": "?",
            "is_active_member": False,
            "joined_on": None,
            "left_on": None,
        }
    return {
        "id": user.pk,
        "username": user.username,
        "name": user.name,
        "display_name": user.display_name,
        "upi_id": user.upi_id,
        "initials": user.initials,
        "is_active_member": user.is_active_member,
        "joined_on": user.joined_on.isoformat() if user.joined_on else None,
        "left_on": user.left_on.isoformat() if user.left_on else None,
    }


def _serialize_category(cat: Category) -> dict:
    return {
        "id": cat.pk,
        "name": cat.name,
        "icon": cat.icon,
        "color": cat.color,
        "behaviour": cat.behaviour,
        "behaviour_label": cat.behaviour_label,
        "prorate_by_tenancy": cat.prorate_by_tenancy,
        "prorate_by_presence": cat.prorate_by_presence,
    }


# ==============================================================================
# Auth & Members
# ==============================================================================

@csrf_exempt
@login_not_required
def auth_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = {}
    if request.body:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            pass

    username = data.get("username") or request.POST.get("username")
    password = data.get("password") or request.POST.get("password")

    if not username:
        return JsonResponse({"error": "Username is required"}, status=400)

    user = None
    if password:
        user = authenticate(request, username=username, password=password)
    elif settings.DEBUG:
        # Easy switcher for demo / LAN debugging if password not passed
        user = User.objects.filter(username=username).first()

    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=400)

    if not user.is_active:
        return JsonResponse({"error": "Account is inactive"}, status=403)

    login(request, user)
    return JsonResponse({
        "ok": True,
        "user": _serialize_user(user),
    })


@csrf_exempt
@login_not_required
def auth_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@login_not_required
def auth_me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False, "user": None}, status=401)
    return JsonResponse({
        "authenticated": True,
        "user": _serialize_user(request.user),
    })


@login_not_required
def members_list(request):
    members = list(User.objects.active_members())
    return JsonResponse({
        "members": [_serialize_user(m) for m in members]
    })


@login_not_required
def categories_list(request):
    categories = Category.objects.all()
    return JsonResponse({
        "categories": [_serialize_category(c) for c in categories]
    })


# ==============================================================================
# Dashboard
# ==============================================================================

@json_auth_required
def dashboard_view(request):
    user = request.user
    today = dt.date.today()

    members = list(User.objects.active_members())
    balances = get_balances(members)
    by_id = {person.pk: person for person in members}

    my_balance_row = get_balance_for(user)
    month_expenses = Expense.objects.countable().for_month(today.year, today.month)

    month_total = month_expenses.aggregate(t=Sum("amount"))["t"] or ZERO
    my_month_share = (
        ExpenseShare.objects.filter(
            user=user,
            expense__is_deleted=False,
            expense__date__year=today.year,
            expense__date__month=today.month,
        ).aggregate(t=Sum("amount_owed"))["t"]
        or ZERO
    )

    transfers = [
        {
            "from_user": _serialize_user(by_id[t.from_user_id]),
            "to_user": _serialize_user(by_id[t.to_user_id]),
            "amount": str(t.amount),
            "involves_me": user.pk in (t.from_user_id, t.to_user_id),
            "i_pay": t.from_user_id == user.pk,
        }
        for t in simplify_debts(balances)
        if t.from_user_id in by_id and t.to_user_id in by_id
    ]

    drafts = [
        {
            "id": d.pk,
            "description": d.description,
            "category": _serialize_category(d.category),
            "date": d.date.isoformat(),
        }
        for d in drafts_needing_amounts()
    ]

    recent_activity = [
        {
            "id": a.pk,
            "actor": a.actor.name if a.actor else "Somebody",
            "action": a.get_action_display(),
            "label": a.label,
            "created_at": a.created_at.isoformat(),
        }
        for a in AuditLog.objects.select_related("actor")[:8]
    ]

    return JsonResponse({
        "my_balance": str(my_balance_row.net),
        "my_balance_magnitude": str(my_balance_row.magnitude),
        "paid": str(my_balance_row.paid),
        "owed": str(my_balance_row.owed),
        "is_owed": my_balance_row.is_owed,
        "owes": my_balance_row.owes,
        "is_settled": my_balance_row.is_settled,
        "month_total": str(month_total),
        "my_month_share": str(my_month_share),
        "transfers": transfers,
        "drafts": drafts,
        "recent_activity": recent_activity,
    })


# ==============================================================================
# Expenses
# ==============================================================================

@json_auth_required
def expense_list(request):
    user = request.user
    qs = Expense.objects.active().with_related()

    year = request.GET.get("year")
    month = request.GET.get("month")
    if year and month:
        try:
            qs = qs.for_month(int(year), int(month))
        except ValueError:
            pass

    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)

    q = request.GET.get("q")
    if q:
        qs = qs.filter(Q(description__icontains=q) | Q(notes__icontains=q))

    expenses_data = []
    for exp in qs[:100]:
        my_share = None
        for s in exp.shares.all():
            if s.user_id == user.pk:
                my_share = str(s.amount_owed)
                break

        expenses_data.append({
            "id": exp.pk,
            "description": exp.description,
            "amount": str(exp.amount) if exp.amount is not None else None,
            "date": exp.date.isoformat(),
            "period_start": exp.period_start.isoformat() if exp.period_start else None,
            "period_end": exp.period_end.isoformat() if exp.period_end else None,
            "split_type": exp.split_type,
            "category": _serialize_category(exp.category),
            "paid_by": _serialize_user(exp.paid_by),
            "is_draft": exp.is_draft,
            "my_share": my_share,
            "shares_count": exp.shares.count(),
        })

    return JsonResponse({
        "expenses": expenses_data,
        "total_count": len(expenses_data),
    })


@json_auth_required
def expense_detail(request, pk: int):
    exp = get_object_or_404(Expense.objects.active().with_related(), pk=pk)

    shares_data = [
        {
            "id": s.pk,
            "user": _serialize_user(s.user),
            "amount_owed": str(s.amount_owed),
            "basis": s.basis,
            "present_days": s.present_days,
            "share_units": s.share_units,
            "percent": str(s.percent) if s.percent is not None else None,
        }
        for s in exp.shares.all().order_by("user_id")
    ]

    comments_data = [
        {
            "id": c.pk,
            "author": _serialize_user(c.author),
            "body": c.body,
            "created_at": c.created_at.isoformat(),
        }
        for c in exp.comments.select_related("author").all()
    ]

    return JsonResponse({
        "id": exp.pk,
        "description": exp.description,
        "amount": str(exp.amount) if exp.amount is not None else None,
        "date": exp.date.isoformat(),
        "period_start": exp.period_start.isoformat() if exp.period_start else None,
        "period_end": exp.period_end.isoformat() if exp.period_end else None,
        "period_days": exp.period_days,
        "split_type": exp.split_type,
        "split_type_label": exp.get_split_type_display(),
        "category": _serialize_category(exp.category),
        "paid_by": _serialize_user(exp.paid_by),
        "created_by": _serialize_user(exp.created_by),
        "notes": exp.notes,
        "receipt_url": exp.receipt.url if exp.receipt else None,
        "is_draft": exp.is_draft,
        "shares": shares_data,
        "comments": comments_data,
        "is_month_closed": is_closed(exp.date),
    })


@csrf_exempt
@json_auth_required
def expense_create(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    post_data = request.POST.copy()
    if not post_data and request.body:
        try:
            data = json.loads(request.body)
            for k, v in data.items():
                if isinstance(v, list):
                    post_data.setlist(k, [str(item) for item in v])
                elif v is not None:
                    post_data[k] = str(v)
        except json.JSONDecodeError:
            pass

    form = ExpenseForm(post_data, request.FILES, actor=request.user)
    if not form.is_valid():
        return JsonResponse({"error": "Validation failed", "errors": form.errors}, status=422)

    try:
        expense = create_expense(form=form, actor=request.user)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({
        "ok": True,
        "id": expense.pk,
        "description": expense.description,
        "amount": str(expense.amount) if expense.amount else None,
    })


@csrf_exempt
@json_auth_required
def expense_update(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    expense = get_object_or_404(Expense.objects.active(), pk=pk)
    if is_closed(expense.date):
        return JsonResponse({"error": "This month is closed and read-only."}, status=403)

    post_data = request.POST.copy()
    if not post_data and request.body:
        try:
            data = json.loads(request.body)
            for k, v in data.items():
                if isinstance(v, list):
                    post_data.setlist(k, [str(item) for item in v])
                elif v is not None:
                    post_data[k] = str(v)
        except json.JSONDecodeError:
            pass

    form = ExpenseForm(post_data, request.FILES, instance=expense, actor=request.user)
    if not form.is_valid():
        return JsonResponse({"error": "Validation failed", "errors": form.errors}, status=422)

    try:
        updated = update_expense(expense=expense, form=form, actor=request.user)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({
        "ok": True,
        "id": updated.pk,
    })


@csrf_exempt
@json_auth_required
def expense_delete(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    expense = get_object_or_404(Expense.objects.active(), pk=pk)
    if is_closed(expense.date):
        return JsonResponse({"error": "This month is closed and read-only."}, status=403)

    try:
        delete_expense(expense=expense, actor=request.user)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"ok": True})


@csrf_exempt
@json_auth_required
def expense_fill_draft(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    expense = get_object_or_404(Expense.objects.active(), pk=pk)
    amount_str = None
    if request.body:
        try:
            data = json.loads(request.body)
            amount_str = data.get("amount")
        except json.JSONDecodeError:
            pass
    if not amount_str:
        amount_str = request.POST.get("amount")

    if not amount_str:
        return JsonResponse({"error": "Amount is required"}, status=400)

    try:
        amount = Decimal(str(amount_str))
        fill_draft_amount(expense=expense, amount=amount, actor=request.user)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"ok": True, "id": expense.pk})


@csrf_exempt
@json_auth_required
def expense_preview(request):
    """Calculates live split math without touching the database."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = {}
    if request.body:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            pass
    if not data:
        data = request.POST

    try:
        amount = Decimal(str(data.get("amount") or "0.00"))
    except Exception:
        amount = ZERO

    split_type = data.get("split_type") or SplitType.EQUAL
    category_id = data.get("category")
    participant_ids = [int(p) for p in data.get("participants", [])]
    payer_id = int(data.get("paid_by") or request.user.pk)

    if not participant_ids or amount <= ZERO:
        return JsonResponse({"shares": []})

    category = None
    if category_id:
        category = Category.objects.filter(pk=category_id).first()

    # Form pseudo expense for weights
    exp_date = dt.date.today()
    period_start = exp_date
    period_end = exp_date
    if data.get("date"):
        try:
            exp_date = dt.date.fromisoformat(data["date"])
            period_start = exp_date
            period_end = exp_date
        except ValueError:
            pass
    if data.get("period_start"):
        try:
            period_start = dt.date.fromisoformat(data["period_start"])
        except ValueError:
            pass
    if data.get("period_end"):
        try:
            period_end = dt.date.fromisoformat(data["period_end"])
        except ValueError:
            pass

    mock_expense = Expense(
        amount=amount,
        category=category,
        paid_by_id=payer_id,
        date=exp_date,
        period_start=period_start,
        period_end=period_end,
        split_type=split_type,
    )

    people = list(User.objects.filter(pk__in=participant_ids))
    weights = weights_for(mock_expense, people)

    # Custom split inputs
    exact = {}
    percent = {}
    shares_weights = {}
    for uid in participant_ids:
        if f"exact_{uid}" in data:
            try:
                exact[uid] = Decimal(str(data[f"exact_{uid}"]))
            except Exception:
                pass
        if f"percent_{uid}" in data:
            try:
                percent[uid] = Decimal(str(data[f"percent_{uid}"]))
            except Exception:
                pass
        if f"units_{uid}" in data:
            try:
                shares_weights[uid] = int(data[f"units_{uid}"])
            except Exception:
                pass

    try:
        calc_map = compute_shares(
            split_type=split_type,
            total=amount,
            payer_id=payer_id,
            participant_ids=participant_ids,
            weights=weights,
            exact_amounts=exact if split_type == SplitType.EXACT else None,
            percents=percent if split_type == SplitType.PERCENT else None,
            share_units=shares_weights if split_type == SplitType.SHARES else None,
        )
    except SplitError as e:
        return JsonResponse({"error": str(e), "shares": []}, status=400)

    user_map = {u.pk: u for u in people}
    shares_output = []
    for uid, owed in calc_map.items():
        u = user_map.get(uid)
        present_day = weights.get(uid) if (weights and category and category.prorate_by_presence) else None
        shares_output.append({
            "user_id": uid,
            "user_name": u.name if u else str(uid),
            "amount_owed": str(owed),
            "present_days": present_day,
            "share_units": shares_weights.get(uid),
            "percent": str(percent[uid]) if uid in percent else None,
        })

    return JsonResponse({"shares": shares_output})


@csrf_exempt
@json_auth_required
def expense_comment(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    expense = get_object_or_404(Expense.objects.active(), pk=pk)
    body = None
    if request.body:
        try:
            body = json.loads(request.body).get("body")
        except json.JSONDecodeError:
            pass
    if not body:
        body = request.POST.get("body")

    if not body or not body.strip():
        return JsonResponse({"error": "Comment body cannot be empty"}, status=400)

    comment = Comment.objects.create(
        expense=expense,
        author=request.user,
        body=body.strip(),
    )
    return JsonResponse({
        "ok": True,
        "comment": {
            "id": comment.pk,
            "author": _serialize_user(comment.author),
            "body": comment.body,
            "created_at": comment.created_at.isoformat(),
        }
    })


# ==============================================================================
# Settlements & UPI
# ==============================================================================

@json_auth_required
def settlements_overview(request):
    user = request.user
    members = list(User.objects.active_members())
    balances = get_balances(members)
    by_id = {m.pk: m for m in members}

    balance_rows = [
        {
            "user": _serialize_user(m),
            "net": str(balances.get(m.pk, ZERO)),
            "is_me": m.pk == user.pk,
        }
        for m in members
    ]

    transfers = [
        {
            "from_user": _serialize_user(by_id[t.from_user_id]),
            "to_user": _serialize_user(by_id[t.to_user_id]),
            "amount": str(t.amount),
            "involves_me": user.pk in (t.from_user_id, t.to_user_id),
            "i_pay": t.from_user_id == user.pk,
        }
        for t in simplify_debts(balances)
        if t.from_user_id in by_id and t.to_user_id in by_id
    ]

    # Pending settlements that I need to confirm
    awaiting_my_confirmation = [
        {
            "id": s.pk,
            "from_user": _serialize_user(s.from_user),
            "to_user": _serialize_user(s.to_user),
            "amount": str(s.amount),
            "date": s.date.isoformat(),
            "method": s.get_method_display(),
            "note": s.note,
            "created_at": s.created_at.isoformat(),
        }
        for s in Settlement.objects.awaiting(user)
    ]

    # Pending settlements that I sent
    my_pending_sent = [
        {
            "id": s.pk,
            "to_user": _serialize_user(s.to_user),
            "amount": str(s.amount),
            "date": s.date.isoformat(),
            "method": s.get_method_display(),
            "note": s.note,
            "status": s.status,
        }
        for s in Settlement.objects.pending().filter(from_user=user).select_related("to_user")
    ]

    # Recent confirmed / rejected history
    history = [
        {
            "id": s.pk,
            "from_user": _serialize_user(s.from_user),
            "to_user": _serialize_user(s.to_user),
            "amount": str(s.amount),
            "date": s.date.isoformat(),
            "status": s.status,
            "status_label": s.get_status_display(),
            "method": s.get_method_display(),
            "confirmed_at": s.confirmed_at.isoformat() if s.confirmed_at else None,
        }
        for s in Settlement.objects.exclude(status=Settlement.Status.PENDING).select_related("from_user", "to_user")[:20]
    ]

    return JsonResponse({
        "balance_rows": balance_rows,
        "transfers": transfers,
        "awaiting_confirmation": awaiting_my_confirmation,
        "my_pending_sent": my_pending_sent,
        "history": history,
    })


@csrf_exempt
@json_auth_required
def settlement_create(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = {}
    if request.body:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            pass
    if not data:
        data = request.POST

    to_user_id = data.get("to_user") or data.get("to_user_id")
    amount_val = data.get("amount")
    method = data.get("method") or Settlement.Method.UPI
    note = data.get("note", "")

    if not to_user_id or not amount_val:
        return JsonResponse({"error": "Recipient and amount are required"}, status=400)

    try:
        to_user = User.objects.get(pk=int(to_user_id))
    except User.DoesNotExist:
        return JsonResponse({"error": "Recipient not found"}, status=404)

    if to_user.pk == request.user.pk:
        return JsonResponse({"error": "You cannot settle up with yourself"}, status=400)

    try:
        amount = Decimal(str(amount_val))
        if amount <= ZERO:
            return JsonResponse({"error": "Amount must be greater than zero"}, status=400)
    except Exception:
        return JsonResponse({"error": "Invalid amount format"}, status=400)

    settlement = Settlement.objects.create(
        from_user=request.user,
        to_user=to_user,
        amount=amount,
        method=method,
        note=note,
    )
    record_create(actor=request.user, instance=settlement)

    return JsonResponse({
        "ok": True,
        "id": settlement.pk,
        "status": settlement.status,
    })


@csrf_exempt
@json_auth_required
def settlement_confirm(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    settlement = get_object_or_404(Settlement, pk=pk)
    if settlement.to_user_id != request.user.pk:
        return JsonResponse({"error": "Only the recipient can confirm this settlement."}, status=403)

    if settlement.status == Settlement.Status.CONFIRMED:
        return JsonResponse({"ok": True, "status": "CONFIRMED"})

    settlement.confirm()
    record_update(actor=request.user, instance=settlement, before={"status": Settlement.Status.PENDING})
    return JsonResponse({"ok": True, "status": "CONFIRMED"})


@csrf_exempt
@json_auth_required
def settlement_reject(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    settlement = get_object_or_404(Settlement, pk=pk)
    if settlement.to_user_id != request.user.pk and settlement.from_user_id != request.user.pk:
        return JsonResponse({"error": "Not authorized to reject this settlement."}, status=403)

    settlement.reject()
    record_update(actor=request.user, instance=settlement, before={"status": Settlement.Status.PENDING})
    return JsonResponse({"ok": True, "status": "REJECTED"})


@json_auth_required
def settlement_qr(request, pk: int):
    settlement = get_object_or_404(Settlement, pk=pk)
    to_user = settlement.to_user

    upi_str = ""
    qr_uri = ""
    if to_user.upi_id:
        upi_str = upi_link(
            upi_id=to_user.upi_id,
            name=to_user.name,
            amount=settlement.amount,
            note=f"FlatSplit: {settlement.note or 'settlement'}",
        )
        qr_uri = payment_qr(
            upi_id=to_user.upi_id,
            name=to_user.name,
            amount=settlement.amount,
            note=f"FlatSplit: {settlement.note or 'settlement'}",
        )

    return JsonResponse({
        "id": settlement.pk,
        "amount": str(settlement.amount),
        "payee_name": to_user.name,
        "upi_id": to_user.upi_id,
        "upi_uri": upi_str,
        "qr_data_uri": qr_uri,
    })


# ==============================================================================
# Recurring
# ==============================================================================

@json_auth_required
def recurring_list(request):
    templates = RecurringExpense.objects.select_related("category", "paid_by").prefetch_related("default_participants").all()
    out = []
    for t in templates:
        out.append({
            "id": t.pk,
            "description": t.description,
            "category": _serialize_category(t.category),
            "amount": str(t.amount) if t.amount is not None else None,
            "is_variable": t.is_variable,
            "split_type": t.split_type,
            "day_of_month": t.day_of_month,
            "frequency": t.frequency,
            "frequency_label": t.get_frequency_display(),
            "is_active": t.is_active,
            "paid_by": _serialize_user(t.paid_by) if t.paid_by else None,
        })
    return JsonResponse({"templates": out})


@csrf_exempt
@json_auth_required
def recurring_generate(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    today = dt.date.today()
    created = generate_for_month(today.year, today.month)
    return JsonResponse({
        "ok": True,
        "created_count": len(created),
    })


# ==============================================================================
# Away Periods
# ==============================================================================

@json_auth_required
def away_list(request):
    user = request.user
    periods = AwayPeriod.objects.select_related("user").order_by("-start_date")
    out = [
        {
            "id": p.pk,
            "user": _serialize_user(p.user),
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
            "days_count": p.days_count,
            "is_mine": p.user_id == user.pk,
        }
        for p in periods
    ]
    return JsonResponse({"away_periods": out})


@csrf_exempt
@json_auth_required
def away_create(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = {}
    if request.body:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            pass
    if not data:
        data = request.POST

    try:
        start_date = dt.date.fromisoformat(data.get("start_date"))
        end_date = dt.date.fromisoformat(data.get("end_date"))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid start_date or end_date format (YYYY-MM-DD required)"}, status=400)

    if end_date < start_date:
        return JsonResponse({"error": "End date cannot be before start date"}, status=400)

    target_user = request.user
    if data.get("user_id") and request.user.is_staff:
        try:
            target_user = User.objects.get(pk=int(data["user_id"]))
        except User.DoesNotExist:
            pass

    away = AwayPeriod.objects.create(
        user=target_user,
        start_date=start_date,
        end_date=end_date,
    )
    return JsonResponse({
        "ok": True,
        "id": away.pk,
        "days_count": away.days_count,
    })


@csrf_exempt
@json_auth_required
def away_delete(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    period = get_object_or_404(AwayPeriod, pk=pk)
    if period.user_id != request.user.pk and not request.user.is_staff:
        return JsonResponse({"error": "Cannot delete another flatmate's away period."}, status=403)

    period.delete()
    return JsonResponse({"ok": True})


# ==============================================================================
# Activity & Audit Log
# ==============================================================================

@json_auth_required
def activity_list(request):
    logs = AuditLog.objects.select_related("actor").order_by("-created_at")[:50]
    out = [
        {
            "id": l.pk,
            "actor": l.actor.name if l.actor else "Somebody",
            "action": l.action,
            "action_label": l.get_action_display(),
            "model": l.model,
            "object_id": l.object_id,
            "label": l.label,
            "changes": l.changes,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
    return JsonResponse({"activity": out})


# ==============================================================================
# Summary (Flat Tab)
# ==============================================================================

@json_auth_required
def summary_view(request):
    today = dt.date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month

    expenses = Expense.objects.countable().for_month(year, month)
    members = list(User.objects.active())

    by_category = list(
        expenses.values("category__name", "category__color")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    grand_total = sum((row["total"] for row in by_category), ZERO)
    for row in by_category:
        row["percent"] = (
            float(row["total"] / grand_total * 100) if grand_total else 0.0
        )
        row["total"] = str(row["total"])

    paid_by_person = {
        row["paid_by"]: row["total"]
        for row in expenses.values("paid_by").annotate(total=Sum("amount"))
    }
    owed_by_person = {
        row["user"]: row["total"]
        for row in ExpenseShare.objects.filter(
            expense__in=expenses
        ).values("user").annotate(total=Sum("amount_owed"))
    }

    per_person = [
        {
            "person": _serialize_user(person),
            "paid": str(paid_by_person.get(person.pk, ZERO)),
            "share": str(owed_by_person.get(person.pk, ZERO)),
            "diff": str(paid_by_person.get(person.pk, ZERO) - owed_by_person.get(person.pk, ZERO)),
            "diff_num": float(paid_by_person.get(person.pk, ZERO) - owed_by_person.get(person.pk, ZERO)),
        }
        for person in members
    ]

    is_closed_month = is_closed(dt.date(year, month, 1))

    prev_m = 12 if month == 1 else month - 1
    prev_y = year - 1 if month == 1 else year
    next_m = 1 if month == 12 else month + 1
    next_y = year + 1 if month == 12 else year

    return JsonResponse({
        "year": year,
        "month": month,
        "month_label": dt.date(year, month, 1).strftime("%B %Y"),
        "grand_total": str(grand_total),
        "expense_count": expenses.count(),
        "is_closed": is_closed_month,
        "prev_year": prev_y,
        "prev_month": prev_m,
        "next_year": next_y,
        "next_month": next_m,
        "by_category": by_category,
        "per_person": per_person,
    })


@csrf_exempt
@json_auth_required
def month_toggle(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    data = {}
    if request.body:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            pass
    if not data:
        data = request.POST

    try:
        year = int(data.get("year", dt.date.today().year))
        month = int(data.get("month", dt.date.today().month))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid year/month"}, status=400)

    action = data.get("action")
    if action == "reopen":
        reopen_month(year=year, month=month, actor=request.user)
    else:
        close_month(year=year, month=month, actor=request.user)

    return JsonResponse({
        "ok": True,
        "is_closed": is_closed(dt.date(year, month, 1)),
    })

