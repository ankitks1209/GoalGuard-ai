"""Owner-confirmed financial plans sharing the ledger's SQLite write transaction.

Actual cash events record self-reported external activity, never execute transfers.
Drafts and previews have no purchase authority. Agent callers never use this API.
"""

from copy import deepcopy
import json
import uuid

from .finance import calculate, cents, fields, financial_terms, normalize_plan, period_end, text
from .ledger import ENCUMBERED, Rejection, canonical, digest


SCHEMA = """
CREATE TABLE IF NOT EXISTS financial_plans (
 id TEXT PRIMARY KEY, household TEXT NOT NULL REFERENCES households(id),
 active INTEGER NOT NULL, starts_at REAL NOT NULL, ends_at REAL NOT NULL,
 spec_json TEXT NOT NULL, confirmed_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_plan ON financial_plans(household) WHERE active=1;
CREATE TABLE IF NOT EXISTS plan_bills (
 plan_id TEXT NOT NULL REFERENCES financial_plans(id), bill_id TEXT NOT NULL,
 name TEXT NOT NULL, amount_cents INTEGER NOT NULL, due_date TEXT NOT NULL,
 paid_cents INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(plan_id,bill_id)
);
CREATE TABLE IF NOT EXISTS plan_goals (
 plan_id TEXT PRIMARY KEY REFERENCES financial_plans(id), goal_id TEXT NOT NULL,
 title TEXT NOT NULL, target_cents INTEGER NOT NULL, saved_cents INTEGER NOT NULL,
 target_date TEXT NOT NULL, contribution_cents INTEGER NOT NULL,
 fulfilled_cents INTEGER NOT NULL DEFAULT 0, schedule_remaining_cents INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS cash_events (
 household TEXT NOT NULL REFERENCES households(id), event_id TEXT NOT NULL,
 plan_id TEXT NOT NULL REFERENCES financial_plans(id), kind TEXT NOT NULL,
 amount_cents INTEGER NOT NULL, reference_id TEXT, delta_cents INTEGER NOT NULL,
 payload_json TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY(household,event_id)
);
CREATE TABLE IF NOT EXISTS plan_events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, household TEXT NOT NULL,
 plan_id TEXT NOT NULL, at REAL NOT NULL, event TEXT NOT NULL, details_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_drafts (
 household TEXT PRIMARY KEY REFERENCES households(id), mode TEXT NOT NULL,
 spec_json TEXT NOT NULL, saved_at REAL NOT NULL
);
"""


class FinancialPlans:
    def __init__(self, ledger):
        self.ledger = ledger

    @staticmethod
    def active(db, household):
        return db.execute("SELECT * FROM financial_plans WHERE household=? AND active=1", (household,)).fetchone()

    @staticmethod
    def data(db, plan):
        spec = json.loads(plan["spec_json"])
        bills = db.execute("SELECT * FROM plan_bills WHERE plan_id=? ORDER BY bill_id", (plan["id"],)).fetchall()
        spec["bills"] = [{"id": b["bill_id"], "name": b["name"], "amount_cents": b["amount_cents"],
                          "due_date": b["due_date"]} for b in bills]
        goal = db.execute("SELECT * FROM plan_goals WHERE plan_id=?", (plan["id"],)).fetchone()
        if goal:
            spec["goal"] = {"id": goal["goal_id"], "title": goal["title"], "target_cents": goal["target_cents"],
                            "current_saved_cents": goal["saved_cents"], "target_date": goal["target_date"],
                            "contribution_cents": goal["contribution_cents"]}
        adjustments = db.execute("SELECT COALESCE(SUM(delta_cents),0) FROM cash_events WHERE plan_id=?", (plan["id"],)).fetchone()[0]
        income = spec["next_income"]
        received = db.execute("""SELECT COALESCE(SUM(amount_cents),0) FROM cash_events
            WHERE plan_id=? AND kind='income' AND reference_id=?""",
            (plan["id"], income["id"] if income else None)).fetchone()[0]
        return spec, {"paid": {b["bill_id"]: b["paid_cents"] for b in bills},
                      "fulfilled": goal["fulfilled_cents"] if goal else 0,
                      "schedule_remaining": goal["schedule_remaining_cents"] if goal else None,
                      "cash_delta": adjustments, "received_income": received}

    @staticmethod
    def totals(db, plan_id):
        rows = db.execute("SELECT state,amount_cents FROM purchases WHERE plan_id=?", (plan_id,)).fetchall()
        return {"spent": sum(r["amount_cents"] for r in rows if r["state"] == "captured"),
                "reserved": sum(r["amount_cents"] for r in rows if r["state"] in ENCUMBERED)}

    def summary(self, db, household, plan):
        spec, extra = self.data(db, plan)
        view = calculate(spec, start_at=plan["starts_at"], end_at=plan["ends_at"],
                         now=self.ledger.now(), **extra, **self.totals(db, plan["id"]))
        return {**view, "household": household, "plan_id": plan["id"],
                "budget_cents": view["cash_base_cents"],
                "policy_version": self.ledger._household(db, household)["policy_version"],
                "period_start": plan["starts_at"], "period_end": plan["ends_at"],
                "timezone": spec["timezone"], "title": spec["title"], "spec": spec}

    def _event(self, db, household, plan, event, **details):
        db.execute("INSERT INTO plan_events(household,plan_id,at,event,details_json) VALUES(?,?,?,?,?)",
                   (household, plan, self.ledger.now(), event, canonical(details)))

    def _release_pre_payment(self, db, household, reason):
        rows = db.execute("SELECT id FROM purchases WHERE household=? AND state IN ('reserved','approved')", (household,)).fetchall()
        for row in rows:
            db.execute("UPDATE purchases SET state='released',permit=NULL WHERE id=?", (row["id"],))
            self.ledger._event(db, row["id"], "released", reason=reason)

    def _preview(self, db, household, raw, mode):
        if mode not in ("activate", "revise", "rollover"):
            raise Rejection("invalid_plan", "Use activate, revise or rollover.")
        now = self.ledger.now()
        spec = normalize_plan(raw, now)
        owner = self.ledger._household(db, household)
        active = self.active(db, household)
        self.ledger._expire(db, household)
        old_spec, old_extra = self.data(db, active) if active else (None, {})
        summary = self.summary(db, household, active) if active else None
        if (mode == "activate") != (active is None):
            raise Rejection("invalid_plan_state", "Activate once; revise or roll over an existing plan.")
        extra = {}
        totals = {"spent": 0, "reserved": 0}
        start, end = now, period_end(now, spec["timezone"])
        changed = True
        if active:
            if spec["currency"] != old_spec["currency"] or spec["timezone"] != old_spec["timezone"]:
                raise Rejection("immutable_period", "Currency and timezone cannot change on an active household plan.")
            if mode == "revise":
                if spec["opening_cash_cents"] != old_spec["opening_cash_cents"]:
                    raise Rejection("cash_event_required", "Record a cash adjustment instead of editing opening cash.")
                start, end = active["starts_at"], active["ends_at"]
                extra = deepcopy(old_extra)
                changed = financial_terms(spec) != financial_terms(old_spec)
                # An edited goal explicitly confirms a new installment. Unchanged
                # goals preserve fulfilled deposits and the original schedule.
                if financial_terms(spec)["goal"] != financial_terms(old_spec)["goal"]:
                    extra.update(fulfilled=0, schedule_remaining=None)
                if not spec["next_income"] or not old_spec["next_income"] or spec["next_income"]["id"] != old_spec["next_income"]["id"]:
                    extra["received_income"] = 0
                for bill in spec["bills"]:
                    if bill["amount_cents"] < extra["paid"].get(bill["id"], 0):
                        raise Rejection("invalid_plan", "A bill total cannot be below its recorded payments.")
                totals = self.totals(db, active["id"])
            else:
                if now < active["ends_at"]:
                    raise Rejection("period_not_ended", "Rollover is available at the next calendar month.")
                if spec["opening_cash_cents"] != summary["cash_base_cents"] - summary["spent_cents"]:
                    raise Rejection("rollover_cash_mismatch", "Next opening cash must equal prior cash minus prior captured spend.")
                incoming = {b["id"]: b for b in spec["bills"]}
                for bill in summary["bills"]:
                    if bill["remaining_cents"]:
                        carried = incoming.get(bill["id"])
                        if not carried or carried["amount_cents"] != bill["remaining_cents"] or carried["due_date"] != bill["due_date"]:
                            raise Rejection("missing_carried_bill", "Carry every unpaid bill ID, remaining amount and due date.")
                if old_spec["goal"]:
                    if not spec["goal"] or spec["goal"]["id"] != old_spec["goal"]["id"] or spec["goal"]["current_saved_cents"] != old_spec["goal"]["current_saved_cents"]:
                        raise Rejection("goal_carry_mismatch", "Carry the existing goal and its recorded savings into the next plan.")
                totals["reserved"] = sum(r["amount_cents"] for r in db.execute(
                    "SELECT amount_cents FROM purchases WHERE household=? AND state='authorized'", (household,)))
        elif db.execute("SELECT 1 FROM purchases WHERE household=? AND state IN ('captured','authorized','authorizing','capturing','voiding','reconcile_pending') LIMIT 1", (household,)).fetchone():
            raise Rejection("legacy_migration_required", "Existing legacy payments need an explicit accounting migration before plan activation.")
        pending = [r["id"] for r in db.execute("SELECT id FROM purchases WHERE household=? AND state IN ('reserved','approved') ORDER BY id", (household,))]
        if changed and mode == "revise":
            pre_total = db.execute("SELECT COALESCE(SUM(amount_cents),0) FROM purchases WHERE household=? AND state IN ('reserved','approved')", (household,)).fetchone()[0]
            totals["reserved"] -= pre_total
        view = calculate(spec, start_at=start, end_at=end, now=now, **extra, **totals)
        inflight = bool(db.execute("SELECT 1 FROM purchases WHERE household=? AND state IN ('authorizing','capturing','voiding','reconcile_pending') LIMIT 1", (household,)).fetchone())
        blocked = "payment_unresolved" if changed and inflight else (None if view["can_propose"] or (active and not changed) else view["status"])
        impact = pending if changed else []
        # Initial activation time is supplied by the server on confirmation. Bind
        # its local date/end, not a changing subsecond timestamp, into the preview.
        binding = {"spec": spec, "mode": mode, "version": owner["policy_version"],
                   "active_plan": active["id"] if active else None,
                   "period_end": end, "view": view, "releases": impact, "blocked": blocked}
        return {"mode": mode, "spec": spec, "summary": view, "policy_version": owner["policy_version"],
                "period_start": start, "period_end": end, "financial_change": changed,
                "releases_purchase_ids": impact, "activation_blocked_by": blocked,
                "preview_hash": digest(binding)}

    def preview(self, household, spec, mode="activate"):
        with self.ledger._transaction() as db:
            result = self._preview(db, household, spec, mode)
            db.execute("INSERT OR REPLACE INTO plan_drafts VALUES(?,?,?,?)",
                       (household, mode, canonical(result["spec"]), self.ledger.now()))
            return result

    def confirm(self, household, spec, mode, preview_hash):
        with self.ledger._transaction() as db:
            preview = self._preview(db, household, spec, mode)
            if preview_hash != preview["preview_hash"]:
                raise Rejection("stale_plan_preview", "The plan or obligations changed; review a fresh preview.")
            if preview["activation_blocked_by"]:
                raise Rejection("plan_not_ready", "Review the plan shortfall or unresolved payment before activation.",
                                status=preview["activation_blocked_by"])
            active = self.active(db, household)
            spec = preview["spec"]
            old_spec, extra = self.data(db, active) if active else (None, {})
            changed = preview["financial_change"]
            if changed:
                self._release_pre_payment(db, household, "financial_policy_changed")
                db.execute("UPDATE households SET policy_version=policy_version+1 WHERE id=?", (household,))
            if mode == "revise":
                plan_id = active["id"]
                old_paid = extra["paid"]
                db.execute("UPDATE financial_plans SET spec_json=?,confirmed_at=? WHERE id=?",
                           (canonical(spec), self.ledger.now(), plan_id))
                same_goal = financial_terms(spec)["goal"] == financial_terms(old_spec)["goal"]
            else:
                plan_id = str(uuid.uuid4())
                if active:
                    db.execute("UPDATE financial_plans SET active=0 WHERE id=?", (active["id"],))
                db.execute("INSERT INTO financial_plans VALUES(?,?,1,?,?,?,?)",
                           (plan_id, household, preview["period_start"], preview["period_end"], canonical(spec), self.ledger.now()))
                # Captured historical purchases stay attached to the old period;
                # authorized obligations move once, preserving their original terms.
                if mode == "rollover":
                    for purchase in db.execute("SELECT id FROM purchases WHERE household=? AND state='authorized'", (household,)).fetchall():
                        self.ledger._event(db, purchase["id"], "carried_to_plan", from_plan=active["id"], to_plan=plan_id)
                    db.execute("UPDATE purchases SET plan_id=? WHERE household=? AND state='authorized'", (plan_id, household))
                old_paid, same_goal = {}, False
            db.execute("DELETE FROM plan_bills WHERE plan_id=?", (plan_id,))
            for bill in spec["bills"]:
                db.execute("INSERT INTO plan_bills VALUES(?,?,?,?,?,?)", (plan_id, bill["id"], bill["name"],
                           bill["amount_cents"], bill["due_date"], old_paid.get(bill["id"], 0)))
            db.execute("DELETE FROM plan_goals WHERE plan_id=?", (plan_id,))
            goal = spec["goal"]
            if goal:
                db.execute("INSERT INTO plan_goals VALUES(?,?,?,?,?,?,?,?,?)", (plan_id, goal["id"], goal["title"],
                           goal["target_cents"], goal["current_saved_cents"], goal["target_date"], goal["contribution_cents"],
                           extra["fulfilled"] if same_goal else 0,
                           extra["schedule_remaining"] if same_goal else max(0, goal["target_cents"] - goal["current_saved_cents"])))
            db.execute("DELETE FROM plan_drafts WHERE household=?", (household,))
            self._event(db, household, plan_id, mode, spec=spec, financial_change=changed,
                        released_purchase_ids=preview["releases_purchase_ids"])
            return self.summary(db, household, self.active(db, household))

    def get(self, household):
        with self.ledger._transaction() as db:
            self.ledger._household(db, household)
            self.ledger._expire(db, household)
            plan = self.active(db, household)
            draft = db.execute("SELECT * FROM plan_drafts WHERE household=?", (household,)).fetchone()
            return {"plan": self.summary(db, household, plan) if plan else None,
                    "draft": {"mode": draft["mode"], "spec": json.loads(draft["spec_json"]), "saved_at": draft["saved_at"]} if draft else None}

    def cash_event(self, household, payload):
        fields(payload, {"event_id", "kind", "amount_cents", "reference_id"})
        event_id, amount = text(payload["event_id"]), cents(payload["amount_cents"])
        kind, ref = payload["kind"], payload["reference_id"]
        if kind not in ("income", "external_inflow", "external_outflow", "bill_payment", "savings_deposit", "refund") or amount == 0:
            raise Rejection("invalid_cash_event", "Use a documented event kind and positive amount.")
        if ref is not None:
            ref = text(ref)
        payload = {"event_id": event_id, "kind": kind, "amount_cents": amount, "reference_id": ref}
        with self.ledger._transaction() as db:
            old = db.execute("SELECT payload_json FROM cash_events WHERE household=? AND event_id=?", (household, event_id)).fetchone()
            if old:
                if old["payload_json"] != canonical(payload):
                    raise Rejection("idempotency_conflict", "Cash event IDs cannot change meaning.")
                return {"recorded": False, "event_id": event_id, "summary": self.ledger._summary(db, household)}
            plan = self.active(db, household)
            if not plan:
                raise Rejection("plan_required", "Confirm a financial plan first.")
            spec, _ = self.data(db, plan)
            if kind == "income" and (not spec["next_income"] or ref != spec["next_income"]["id"]):
                raise Rejection("invalid_cash_event", "Link income to the current expected receipt ID.")
            if kind in ("external_inflow", "external_outflow") and ref is not None:
                raise Rejection("invalid_cash_event", "Unlinked cash corrections require a null reference.")
            if kind == "bill_payment":
                bill = db.execute("SELECT * FROM plan_bills WHERE plan_id=? AND bill_id=?", (plan["id"], ref)).fetchone()
                if not bill or amount > bill["amount_cents"] - bill["paid_cents"]:
                    raise Rejection("invalid_cash_event", "Payment must fit the unpaid bill balance.")
                db.execute("UPDATE plan_bills SET paid_cents=paid_cents+? WHERE plan_id=? AND bill_id=?", (amount, plan["id"], ref))
            if kind == "savings_deposit":
                if not spec["goal"] or ref != spec["goal"]["id"]:
                    raise Rejection("invalid_cash_event", "Link the savings deposit to the current goal.")
                cents(spec["goal"]["current_saved_cents"] + amount)
                db.execute("UPDATE plan_goals SET saved_cents=saved_cents+?,fulfilled_cents=fulfilled_cents+? WHERE plan_id=?", (amount, amount, plan["id"]))
            if kind == "refund":
                purchase = self.ledger._purchase(db, ref)
                refunded = db.execute("SELECT COALESCE(SUM(amount_cents),0) FROM cash_events WHERE household=? AND kind='refund' AND reference_id=?", (household, ref)).fetchone()[0]
                if purchase["household"] != household or purchase["state"] != "captured" or refunded + amount > purchase["amount_cents"]:
                    raise Rejection("invalid_cash_event", "Received refunds must fit a captured purchase's unrefunded amount.")
            delta = amount if kind in ("income", "external_inflow", "refund") else -amount
            db.execute("INSERT INTO cash_events VALUES(?,?,?,?,?,?,?,?,?)", (household, event_id, plan["id"], kind, amount, ref, delta, canonical(payload), self.ledger.now()))
            # Record real-world truth even during an uncertain payment or deficit.
            # Only pre-payment proposals are released; payment obligations survive.
            self._release_pre_payment(db, household, "cash_records_changed")
            db.execute("UPDATE households SET policy_version=policy_version+1 WHERE id=?", (household,))
            self._event(db, household, plan["id"], "cash_recorded", **payload)
            return {"recorded": True, "event_id": event_id, "summary": self.summary(db, household, plan)}

    def audit(self, household):
        with self.ledger._transaction() as db:
            self.ledger._household(db, household)
            return {"events": [{"sequence": r["sequence"], "at": r["at"], "plan_id": r["plan_id"],
                                "event": r["event"], "details": json.loads(r["details_json"])}
                               for r in db.execute("SELECT * FROM plan_events WHERE household=? ORDER BY sequence", (household,))]}
