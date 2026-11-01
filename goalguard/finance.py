"""Deterministic USD plan validation and arithmetic; no model or payment I/O."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .ledger import Rejection


MAX_CENTS = 1_000_000_000_000


def fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise Rejection("invalid_plan", "Provide exactly the documented plan fields.")


def text(value, limit=120):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise Rejection("invalid_plan", "A bounded nonempty label is required.")
    return value.strip()


def cents(value):
    if type(value) is not int or not 0 <= value <= MAX_CENTS:
        raise Rejection("invalid_money", "Use bounded nonnegative integer USD cents.")
    return value


def day(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or parsed.year > 9998:
            raise ValueError()
        return parsed
    except (TypeError, ValueError):
        raise Rejection("invalid_plan", "Use a valid YYYY-MM-DD date before year 9999.") from None


def local_day(now, zone):
    return datetime.fromtimestamp(now, ZoneInfo(zone)).date()


def period_end(now, zone):
    current = local_day(now, zone)
    end = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return datetime.combine(end, time.min, ZoneInfo(zone)).timestamp()


def normalize_plan(spec, now):
    fields(spec, {"title", "timezone", "currency", "opening_cash_cents", "buffer_cents",
                  "next_income", "bills", "goal"})
    zone = text(spec["timezone"])
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise Rejection("invalid_plan", "Use an installed IANA timezone.") from None
    if spec["currency"] != "USD":
        raise Rejection("invalid_plan", "This prototype supports USD only.")
    result = {"title": text(spec["title"]), "timezone": zone, "currency": "USD",
              "opening_cash_cents": cents(spec["opening_cash_cents"]),
              "buffer_cents": cents(spec["buffer_cents"])}
    income = spec["next_income"]
    if income is not None:
        fields(income, {"id", "due_date", "amount_cents"})
        income = {"id": text(income["id"]), "due_date": day(income["due_date"]).isoformat(),
                  "amount_cents": cents(income["amount_cents"])}
        if income["amount_cents"] == 0:
            raise Rejection("invalid_plan", "Expected income must be positive or omitted.")
    result["next_income"] = income
    if not isinstance(spec["bills"], list) or len(spec["bills"]) > 100:
        raise Rejection("invalid_plan", "At most 100 explicit bills are supported.")
    bills = []
    for bill in spec["bills"]:
        fields(bill, {"id", "name", "amount_cents", "due_date"})
        bills.append({"id": text(bill["id"]), "name": text(bill["name"]),
                      "amount_cents": cents(bill["amount_cents"]),
                      "due_date": day(bill["due_date"]).isoformat()})
    if len({b["id"] for b in bills}) != len(bills):
        raise Rejection("invalid_plan", "Bill IDs must be unique, including overdue bills.")
    result["bills"] = sorted(bills, key=lambda b: b["id"])
    goal = spec["goal"]
    if goal is not None:
        fields(goal, {"id", "title", "target_cents", "current_saved_cents", "target_date", "contribution_cents"})
        goal = {"id": text(goal["id"]), "title": text(goal["title"]),
                "target_cents": cents(goal["target_cents"]),
                "current_saved_cents": cents(goal["current_saved_cents"]),
                "target_date": day(goal["target_date"]).isoformat(),
                "contribution_cents": cents(goal["contribution_cents"])}
        if goal["target_cents"] > goal["current_saved_cents"] and day(goal["target_date"]) < local_day(now, zone):
            raise Rejection("invalid_plan", "An unfinished goal cannot have a past deadline.")
    result["goal"] = goal
    return result


def financial_terms(spec):
    """Titles and expected income amount alone cannot change spending authority."""
    result = {k: v for k, v in spec.items() if k != "title"}
    result["bills"] = [{k: v for k, v in b.items() if k != "name"} for b in spec["bills"]]
    if spec["goal"]:
        result["goal"] = {k: v for k, v in spec["goal"].items() if k != "title"}
    if spec["next_income"]:
        result["next_income"] = {k: v for k, v in spec["next_income"].items() if k != "amount_cents"}
    return result


def calculate(spec, *, start_at, end_at, now, paid=None, fulfilled=0,
              cash_delta=0, received_income=0, spent=0, reserved=0, schedule_remaining=None):
    paid = paid or {}
    zone = spec["timezone"]
    today = local_day(now, zone)
    income = spec["next_income"]
    end_day = local_day(end_at, zone)
    cutoff = max(end_day, day(income["due_date"]) + timedelta(days=1)) if income else end_day
    bills = [{**b, "paid_cents": paid.get(b["id"], 0),
              "remaining_cents": max(0, b["amount_cents"] - paid.get(b["id"], 0)),
              "protected": day(b["due_date"]) < cutoff} for b in spec["bills"]]
    protected_bills = sum(b["remaining_cents"] for b in bills if b["protected"])
    goal = spec["goal"]
    goal_view = None
    remaining_contribution = 0
    if goal:
        first = local_day(start_at, zone)
        deadline = day(goal["target_date"])
        periods = max(1, (deadline.year - first.year) * 12 + deadline.month - first.month + 1)
        # Transfers lower the unfulfilled fixed installment, never recalculate it.
        remaining = max(0, goal["target_cents"] - goal["current_saved_cents"])
        initial_remaining = remaining if schedule_remaining is None else schedule_remaining
        suggested = (initial_remaining + periods - 1) // periods
        remaining_contribution = max(0, min(goal["contribution_cents"], initial_remaining) - fulfilled)
        goal_view = {**goal, "contribution_opportunities": periods,
                     "suggested_contribution_cents": suggested,
                     "remaining_goal_cents": remaining,
                     "fulfilled_cents": fulfilled,
                     "remaining_contribution_cents": remaining_contribution,
                     "schedule_off_track": goal["contribution_cents"] * periods < initial_remaining,
                     "partial_month_counts_in_full": True, "assumed_return_percent": 0}
    protected = protected_bills + spec["buffer_cents"] + remaining_contribution
    cash = spec["opening_cash_cents"] + cash_delta
    available = cash - protected - spent - reserved
    expected = max(0, income["amount_cents"] - received_income) if income else 0
    forecast = available + expected
    if now >= end_at:
        status = "rollover_required"
    elif income is None:
        status = "needs_income_date"
    elif received_income >= income["amount_cents"]:
        status = "needs_next_income"
    elif day(income["due_date"]) < today and received_income < income["amount_cents"]:
        status = "income_overdue"
    elif forecast < 0:
        status = "infeasible"
    elif available < 0:
        status = "waiting_for_income"
    else:
        status = "zero_capacity" if available == 0 else "ready"
    return {"currency": "USD", "cash_base_cents": cash, "protected_bills_cents": protected_bills,
            "buffer_cents": spec["buffer_cents"], "remaining_goal_contribution_cents": remaining_contribution,
            "protected_cents": protected, "spent_cents": spent, "encumbered_cents": reserved,
            "available_cents": available, "projected_surplus_cents": forecast,
            "expected_unreceived_income_cents": expected, "shortfall_cents": max(0, -available),
            "bill_cutoff_exclusive": cutoff.isoformat(), "bills": bills, "goal": goal_view,
            "status": status, "can_propose": status in ("ready", "zero_capacity")}
