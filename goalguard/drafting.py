"""Owner-requested initial plan extraction; no tools, activation or payment I/O."""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from importlib.resources import files
import json
import re
import time
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .finance import calculate, cents, day, fields, local_day, normalize_plan, period_end, text
from .ledger import Rejection


ROOT_FIELDS = {"opening_cash", "buffer", "income", "bills", "goal", "no_income_quote",
               "no_bills_quote", "no_goal_quote", "unsupported_currency_quotes", "clarifications"}
MONEY = re.compile(r"(?:\$\s*|USD\s*)?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)", re.I)
NON_USD = re.compile(r"\b(?:INR|EUR|GBP|CAD|AUD|JPY|CNY|RMB|rupees|euros|yen)\b", re.I)


def validate_input(request, zone, currency, allow_model_processing):
    if allow_model_processing is not True:
        raise Rejection("model_consent_required", "Explicitly allow this text to be sent to the model, or use manual entry.")
    if not isinstance(request, str) or not 1 <= len(request.strip()) <= 4000:
        raise Rejection("invalid_plan", "Provide an owner request of at most 4,000 characters.")
    if currency != "USD":
        raise Rejection("invalid_plan", "The draft helper supports USD only; no currency conversion is performed.")
    if not isinstance(zone, str) or not 1 <= len(zone) <= 120:
        raise Rejection("invalid_plan", "Provide an IANA timezone.")
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise Rejection("invalid_plan", "Provide an installed IANA timezone.") from None


def validate_extraction(value):
    """Enforce the fixed local contract even if the provider ignores its schema."""
    fields(value, ROOT_FIELDS)
    def quote(v):
        if v is not None and (not isinstance(v, str) or len(v) > 240):
            raise Rejection("invalid_plan", "Invalid extracted quote.")
    for key in ("opening_cash", "buffer", "no_income_quote", "no_bills_quote", "no_goal_quote"):
        quote(value[key])
    for key in ("income", "goal"):
        if value[key] is not None:
            expected = {"amount", "date"} if key == "income" else {"title", "target", "saved", "date", "contribution"}
            fields(value[key], expected)
            for v in value[key].values():
                quote(v)
    if value["bills"] is not None:
        if not isinstance(value["bills"], list) or len(value["bills"]) > 20:
            raise Rejection("invalid_plan", "The draft helper supports at most twenty bills.")
        for bill in value["bills"]:
            fields(bill, {"name", "amount", "date"})
            for v in bill.values():
                quote(v)
    for key in ("unsupported_currency_quotes", "clarifications"):
        if (not isinstance(value[key], list) or len(value[key]) > 8
                or any(not isinstance(v, str) or not 1 <= len(v.strip()) <= 240 for v in value[key])):
            raise Rejection("invalid_plan", "Invalid extracted clarification.")


def assemble_draft(extracted, request, zone, now):
    issues, questions, computed = [], [], []

    def issue(field, code, question):
        issues.append({"field": field, "code": code})
        if question not in questions:
            questions.append(question)

    def span(value, field, question):
        if value is None or not value.strip():
            issue(field, "missing", question)
            return None
        value = value.strip()
        if value not in request:
            issue(field, "not_in_request", question)
            return None
        return value

    def money(value, field, question):
        raw = span(value, field, question)
        if raw is None:
            return None
        match = MONEY.fullmatch(raw)
        # Do not accept a quoted substring of a larger numeric token.
        anchored = re.search(r"(?<![\d.,+−-])" + re.escape(raw) + r"(?!\d|[.,]\d|[%−-])(?!\s*%)", request)
        signed_prefix = anchored and re.search(r"[+−-]\s*(?:\$|USD)?\s*$", request[max(0, anchored.start() - 20):anchored.start()], re.I)
        if not match or not anchored or signed_prefix:
            issue(field, "invalid_amount_literal", question)
            return None
        try:
            return cents(int(Decimal(match[1].replace(",", "")) * 100))
        except (ValueError, Rejection):
            issue(field, "invalid_money", question)
            return None

    def date_value(value, field, question):
        raw = span(value, field, question)
        if raw is None:
            return None
        try:
            return day(raw).isoformat()
        except Rejection:
            issue(field, "explicit_date_required", question)
            return None

    def none_statement(value, field):
        if value is None:
            return False
        raw = span(value, field, "Explicitly state whether this item is absent.")
        if raw and re.search(r"\b(?:no|none|not|without|don't)\b", raw, re.I):
            return True
        issue(field, "explicit_none_required", "Explicitly state whether this item is absent.")
        return False

    def label(value, field, default):
        if value is None:
            computed.append(field)
            return default
        match = re.search(re.escape(value.strip()), request, re.I)
        if not match or not value.strip():
            issue(field, "not_in_request", "Provide a name for the bill or savings goal, or leave it unnamed.")
            return default
        return text(match[0])

    cash = money(extracted["opening_cash"], "opening_cash", "How much USD cash is available now, excluding separately held savings?")
    buffer = money(extracted["buffer"], "buffer", "What USD cash buffer should be protected? State $0 explicitly if none.")
    no_income = none_statement(extracted["no_income_quote"], "no_income_quote")
    income = extracted["income"]
    if income is not None and no_income:
        issue("income", "conflicting_input", "Clarify whether upcoming income exists.")
    if income is None and not no_income:
        issue("income", "missing", "Give the next expected income amount and YYYY-MM-DD date, or explicitly state there is no expected income.")
    income_spec = None if income is None else {
        "id": "draft-income", "amount_cents": money(income["amount"], "income.amount", "What is the next expected USD income amount?"),
        "due_date": date_value(income["date"], "income.date", "What is the next expected income date (YYYY-MM-DD)?")}

    no_bills = none_statement(extracted["no_bills_quote"], "no_bills_quote")
    bills = extracted["bills"]
    if bills and no_bills:
        issue("bills", "conflicting_input", "Clarify which unpaid bills need protection.")
    if not bills and not no_bills:
        issue("bills", "missing", "List unpaid bills with USD amounts and YYYY-MM-DD dates, or explicitly state there are no bills.")
    bill_specs = []
    for i, bill in enumerate(bills or []):
        prefix = f"bills[{i}]"
        bill_specs.append({"id": f"draft-bill-{i + 1}", "name": label(bill["name"], prefix + ".name", f"Bill {i + 1}"),
                           "amount_cents": money(bill["amount"], prefix + ".amount", f"What is bill {i + 1}'s USD amount?"),
                           "due_date": date_value(bill["date"], prefix + ".date", f"What is bill {i + 1}'s due date (YYYY-MM-DD)?")})
    no_goal = none_statement(extracted["no_goal_quote"], "no_goal_quote")
    goal = extracted["goal"]
    if goal is not None and no_goal:
        issue("goal", "conflicting_input", "Clarify whether a savings goal should be protected.")
    if goal is None and not no_goal:
        issue("goal", "missing", "Give a savings target, separately saved amount and YYYY-MM-DD deadline, or explicitly state there is no savings goal.")
    goal_spec = None
    if goal is not None:
        goal_spec = {"id": "draft-goal", "title": label(goal["title"], "goal.title", "Savings target"),
                     "target_cents": money(goal["target"], "goal.target", "What is the total USD savings target?"),
                     "current_saved_cents": money(goal["saved"], "goal.saved", "How much USD is already saved separately toward this target? State $0 explicitly if none."),
                     "target_date": date_value(goal["date"], "goal.date", "What is the goal deadline (YYYY-MM-DD)?"),
                     "contribution_cents": 0 if goal["contribution"] is None else money(
                         goal["contribution"], "goal.contribution", "What USD monthly contribution did you intend?")}
    for quote in extracted["unsupported_currency_quotes"]:
        if quote in request:
            issue("currency", "unsupported_currency", "Use USD amounts only; no currency conversion was performed.")
        else:
            issue("currency", "unverified_currency_quote", "Confirm that all amounts are USD.")
    for question in extracted["clarifications"]:
        issue("request", "model_clarification", question.strip())
    response = {"status": "needs_clarification", "plan": None, "questions": questions[:8], "issues": issues,
                "computed_fields": computed, "requires_owner_confirmation": True,
                "manual_entry_available": True,
                "assumptions": ["Review every amount, date and bill; source quotes do not prove semantic completeness.",
                                "Opening cash excludes separately held savings. Expected income is forecast only.",
                                "Initial plan only; full contribution for a partial first month, zero assumed investment return."]}
    if issues:
        return response
    spec = {"title": "Draft household plan", "currency": "USD", "timezone": zone,
            "opening_cash_cents": cash, "buffer_cents": buffer, "next_income": income_spec,
            "bills": bill_specs, "goal": goal_spec}
    try:
        spec = normalize_plan(spec, now)
        if goal is not None and goal["contribution"] is None:
            view = calculate(spec, start_at=now, end_at=period_end(now, zone), now=now)
            spec["goal"]["contribution_cents"] = view["goal"]["suggested_contribution_cents"]
            computed.append("goal.contribution_cents")
        view = calculate(spec, start_at=now, end_at=period_end(now, zone), now=now)
    except Rejection as error:
        response["issues"] = [{"field": "plan", "code": error.code}]
        response["questions"] = ["Review the entered amounts and dates, including any unfinished goal deadline, or use manual entry."]
        return response
    response.update(status="draft_ready", plan=spec, calculation=view)
    return response


class PlanDrafter:
    def __init__(self, provider):
        self.provider = provider
        resources = files("goalguard").joinpath("resources")
        self.prompt = resources.joinpath("plan-draft.txt").read_text()
        self.schema = json.loads(resources.joinpath("plan-draft.schema.json").read_text())

    def draft(self, request, zone, currency, allow_model_processing, *, clock=time.time):
        validate_input(request, zone, currency, allow_model_processing)
        if NON_USD.search(request) or any(unicodedata.category(c) == "Sc" and c != "$" for c in request):
            return {"status": "needs_manual_entry", "plan": None, "model_call_attempted": False,
                    "questions": ["Enter USD amounts only; no currency conversion is available."],
                    "issues": [{"field": "currency", "code": "unsupported_currency"}],
                    "manual_entry_available": True, "requires_owner_confirmation": True}
        context = {"owner_text": request, "timezone": zone, "currency": currency,
                   "as_of_date": local_day(clock(), zone).isoformat()}
        turn = self.provider.extract(json.dumps(context), self.prompt, self.schema)
        try:
            validate_extraction(turn.value)
            result = assemble_draft(turn.value, request, zone, clock())
        except Rejection:
            result = {"status": "needs_manual_entry", "plan": None,
                      "questions": ["The model output did not pass local validation. Use manual entry or clarify the request."],
                      "issues": [{"field": "model_output", "code": "invalid_draft_schema"}],
                      "manual_entry_available": True, "requires_owner_confirmation": True}
        result.update(model_call_attempted=True, provider=self.provider.provider, model=self.provider.model,
                      model_version=turn.model_version, usage=turn.usage,
                      generated_at_utc=datetime.now(timezone.utc).isoformat(),
                      prompt_sha256=hashlib.sha256(self.prompt.encode()).hexdigest(),
                      schema_sha256=hashlib.sha256(json.dumps(self.schema, sort_keys=True).encode()).hexdigest())
        return result
