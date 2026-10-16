"""Money is integer USD cents. SQLite serializes writers across this prototype DB.

No model output is accepted as payment consent. Payment I/O happens outside the
transaction, between begin_payment and finish_payment, with a durable operation ID.
"""

from __future__ import annotations

import base64
from contextlib import closing, contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Callable
import uuid


ENCUMBERED = (
    "reserved", "approved", "authorizing", "authorized", "capturing",
    "voiding", "reconcile_pending",
)
TERMINAL = ("captured", "released", "expired", "voided")
PAYMENT_STARTS = {
    "authorize": ("approved", "authorizing"),
    "capture": ("authorized", "capturing"),
    "void": ("authorized", "voiding"),
}
PAYMENT_ENDS = {"authorize": "authorized", "capture": "captured", "void": "voided"}


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Rejection(Exception):
    def __init__(self, code: str, message: str, **details: object):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict:
        return {"decision": "denied", "reason": self.code,
                "message": self.message, "details": self.details}


def positive_cents(value: int, *, allow_zero: bool = False) -> None:
    if type(value) is not int or value < (0 if allow_zero else 1):
        raise Rejection("invalid_money", "Use non-negative integer cents.")


@dataclass(frozen=True)
class Item:
    sku: str
    quantity: int
    unit_cents: int


@dataclass(frozen=True)
class Cart:
    merchant: str
    items: tuple[Item, ...]
    shipping_cents: int = 0
    tax_cents: int = 0
    currency: str = "USD"

    def as_dict(self) -> dict:
        if self.currency != "USD" or not self.merchant or not self.items:
            raise Rejection("invalid_cart", "A USD merchant cart with items is required.")
        positive_cents(self.shipping_cents, allow_zero=True)
        positive_cents(self.tax_cents, allow_zero=True)
        skus = set()
        items = []
        for item in sorted(self.items, key=lambda item: item.sku):
            if not item.sku or item.sku in skus:
                raise Rejection("invalid_cart", "Each SKU must appear exactly once.")
            if type(item.quantity) is not int or not 1 <= item.quantity <= 100:
                raise Rejection("invalid_cart", "Quantity must be an integer from 1 to 100.")
            positive_cents(item.unit_cents)
            skus.add(item.sku)
            items.append({"sku": item.sku, "quantity": item.quantity,
                          "unit_cents": item.unit_cents})
        return {"merchant": self.merchant, "currency": self.currency,
                "items": items, "shipping_cents": self.shipping_cents,
                "tax_cents": self.tax_cents}

    @property
    def total_cents(self) -> int:
        cart = self.as_dict()
        return sum(i["quantity"] * i["unit_cents"] for i in cart["items"]) + (
            self.shipping_cents + self.tax_cents)

    @property
    def cart_hash(self) -> str:
        return digest(self.as_dict())


class Ledger:
    def __init__(self, path: str | Path, *, now: Callable[[], float] = time.time,
                 ttl_seconds: int = 900, signing_key_path: str | Path | None = None):
        if type(ttl_seconds) is not int or ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.path = str(path)
        self.now = now
        self.ttl_seconds = ttl_seconds
        self.signing_key_path = Path(signing_key_path or (self.path + ".signing-key"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connection()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS households (
                    id TEXT PRIMARY KEY,
                    budget_cents INTEGER NOT NULL CHECK(budget_cents >= 0),
                    protected_cents INTEGER NOT NULL CHECK(protected_cents >= 0),
                    policy_version INTEGER NOT NULL DEFAULT 1,
                    CHECK(protected_cents <= budget_cents)
                );
                CREATE TABLE IF NOT EXISTS purchases (
                    id TEXT PRIMARY KEY,
                    household TEXT NOT NULL REFERENCES households(id),
                    agent TEXT NOT NULL,
                    request_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    cart_json TEXT NOT NULL,
                    cart_hash TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    state TEXT NOT NULL CHECK(state IN (
                        'reserved','approved','authorizing','authorized','capturing',
                        'voiding','reconcile_pending','captured','released','expired','voided'
                    )),
                    expires_at REAL NOT NULL,
                    policy_version INTEGER NOT NULL,
                    permit TEXT,
                    permit_consumed_at REAL,
                    order_id TEXT UNIQUE,
                    authorization_id TEXT UNIQUE,
                    capture_id TEXT UNIQUE,
                    UNIQUE(household, agent, request_key)
                );
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    purchase TEXT NOT NULL REFERENCES purchases(id),
                    action TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_json TEXT,
                    intent_json TEXT,
                    UNIQUE(purchase, action)
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    purchase TEXT NOT NULL,
                    at REAL NOT NULL,
                    event TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proposal_attempts (
                    household TEXT NOT NULL REFERENCES households(id),
                    agent TEXT NOT NULL,
                    period_id TEXT NOT NULL,
                    request_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    PRIMARY KEY(household, agent, period_id, request_key)
                );
            """)
        with self._transaction() as db:
            # Upgrade existing local prototypes without rotating live permissions.
            for table, column, definition in (
                ("purchases", "permit_consumed_at", "REAL"),
                ("operations", "intent_json", "TEXT"),
            ):
                names = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
                if column not in names:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            old = db.execute("SELECT value FROM settings WHERE key='signing_key'").fetchone()
            self.signing_key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not self.signing_key_path.exists():
                # Never silently rotate the signing key for outstanding consents.
                if old is None and db.execute("SELECT 1 FROM purchases WHERE permit IS NOT NULL LIMIT 1").fetchone():
                    raise RuntimeError("Signing key missing for existing approvals; recover the key before continuing.")
                value = old["value"] if old else secrets.token_hex(32)
                descriptor = os.open(self.signing_key_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(descriptor, "w") as file:
                    file.write(value)
                    file.flush()
                    os.fsync(file.fileno())
            self.key = bytes.fromhex(self.signing_key_path.read_text())
            if len(self.key) != 32:
                raise RuntimeError("Signing key must be 32 bytes")
            if old:
                db.execute("DELETE FROM settings WHERE key='signing_key'")

    def _connection(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @contextmanager
    def _transaction(self):
        db = self._connection()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _event(self, db, purchase: str, event: str, **details):
        db.execute("INSERT INTO events(purchase,at,event,details_json) VALUES(?,?,?,?)",
                   (purchase, self.now(), event, canonical(details)))

    def _household(self, db, household: str):
        row = db.execute("SELECT * FROM households WHERE id=?", (household,)).fetchone()
        if row is None:
            raise Rejection("unknown_household", "Household does not exist.")
        return row

    def _purchase(self, db, purchase: str):
        row = db.execute("SELECT * FROM purchases WHERE id=?", (purchase,)).fetchone()
        if row is None:
            raise Rejection("unknown_purchase", "Purchase does not exist.")
        return row

    def _summary(self, db, household: str) -> dict:
        owner = self._household(db, household)
        rows = db.execute("SELECT state,amount_cents FROM purchases WHERE household=?",
                          (household,)).fetchall()
        spent = sum(r["amount_cents"] for r in rows if r["state"] == "captured")
        encumbered = sum(r["amount_cents"] for r in rows if r["state"] in ENCUMBERED)
        available = owner["budget_cents"] - owner["protected_cents"] - spent - encumbered
        if available < 0:
            raise RuntimeError("Budget invariant violated")
        return {"household": household, "currency": "USD",
                "budget_cents": owner["budget_cents"],
                "protected_cents": owner["protected_cents"], "spent_cents": spent,
                "encumbered_cents": encumbered, "available_cents": available,
                "policy_version": owner["policy_version"]}

    def _expire(self, db, household: str):
        # Once payment I/O starts, local expiry must never assume no money moved.
        rows = db.execute("""SELECT id FROM purchases WHERE household=?
            AND state IN ('reserved','approved') AND expires_at <= ?""",
                          (household, self.now())).fetchall()
        for row in rows:
            db.execute("UPDATE purchases SET state='expired' WHERE id=?", (row["id"],))
            self._event(db, row["id"], "expired", reason="pre_authorization_ttl")

    def create_household(self, household: str, budget_cents: int, protected_cents: int):
        positive_cents(budget_cents, allow_zero=True)
        positive_cents(protected_cents, allow_zero=True)
        if not household or protected_cents > budget_cents:
            raise Rejection("invalid_budget", "Protected money must fit within the budget.")
        with self._transaction() as db:
            db.execute("INSERT INTO households(id,budget_cents,protected_cents) VALUES(?,?,?)",
                       (household, budget_cents, protected_cents))
            return self._summary(db, household)

    def summary(self, household: str):
        with self._transaction() as db:
            self._expire(db, household)
            return self._summary(db, household)

    def sweep(self, household: str):
        return self.summary(household)

    def claim_proposal(self, household, agent, period_id, request_key, request_hash, limit):
        """Count distinct proposals, including denials, durably before evaluation.

        Same-key, same-cart transport retries reuse a slot; changing the cart under
        that key is rejected. The trusted host, never an agent, chooses period_id.
        """
        if not isinstance(request_key, str) or not 1 <= len(request_key) <= 128:
            raise Rejection("invalid_request", "A bounded request key is required.")
        with self._transaction() as db:
            self._household(db, household)
            old = db.execute("""SELECT request_hash FROM proposal_attempts WHERE
                household=? AND agent=? AND period_id=? AND request_key=?""",
                (household, agent, period_id, request_key)).fetchone()
            if old:
                if old["request_hash"] != request_hash:
                    raise Rejection("idempotency_conflict", "Request key cannot change its cart.")
                return
            used = db.execute("""SELECT COUNT(*) FROM proposal_attempts WHERE
                household=? AND agent=? AND period_id=?""", (household, agent, period_id)).fetchone()[0]
            if used >= limit:
                raise Rejection("proposal_limit", "Proposal allowance exhausted.")
            db.execute("INSERT INTO proposal_attempts VALUES(?,?,?,?,?)",
                       (household, agent, period_id, request_key, request_hash))

    def reserve(self, household: str, agent: str, cart: Cart, request_key: str):
        if not agent or not request_key or len(request_key) > 128:
            raise Rejection("invalid_request", "Agent and request key are required.")
        cart_json = canonical(cart.as_dict())
        with self._transaction() as db:
            self._expire(db, household)
            old = db.execute("""SELECT * FROM purchases WHERE household=?
                AND agent=? AND request_key=?""", (household, agent, request_key)).fetchone()
            if old:
                if old["request_hash"] != cart.cart_hash:
                    raise Rejection("idempotency_conflict", "This request key belongs to a different cart.")
                return self._public(old)
            summary = self._summary(db, household)
            if cart.total_cents > summary["available_cents"]:
                # No reservation is committed on denial.
                raise Rejection("budget_exceeded", "The purchase would consume protected or committed money.",
                                available_cents=summary["available_cents"],
                                requested_cents=cart.total_cents,
                                maximum_total_cents=summary["available_cents"])
            purchase = str(uuid.uuid4())
            db.execute("""INSERT INTO purchases(id,household,agent,request_key,request_hash,
                cart_json,cart_hash,amount_cents,state,expires_at,policy_version)
                VALUES(?,?,?,?,?,?,?,?,'reserved',?,?)""",
                       (purchase, household, agent, request_key, cart.cart_hash,
                        cart_json, cart.cart_hash, cart.total_cents,
                        self.now() + self.ttl_seconds, summary["policy_version"]))
            self._event(db, purchase, "reserved", amount_cents=cart.total_cents, agent=agent)
            self._summary(db, household)
            return self._public(self._purchase(db, purchase))

    def _sign(self, payload: dict) -> str:
        body = base64.urlsafe_b64encode(canonical(payload).encode()).decode().rstrip("=")
        signature = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
        return body + "." + signature

    def _check_permit(self, row, permit: str):
        try:
            body, signature = permit.rsplit(".", 1)
            expected = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected) or not hmac.compare_digest(permit, row["permit"] or ""):
                raise ValueError("invalid signature")
        except (ValueError, AttributeError):
            raise Rejection("invalid_approval", "A valid purchase-specific approval is required.") from None

    def _check_cart(self, row, cart: Cart):
        if cart.cart_hash != row["cart_hash"] or cart.total_cents != row["amount_cents"]:
            raise Rejection("cart_changed", "Merchant, items, price, currency or delivered total changed; request a new approval.")

    def approve(self, purchase: str, current_cart: Cart):
        # Only a trusted owner endpoint may invoke this, never an agent tool.
        failure = None
        result = None
        with self._transaction() as db:
            row = self._purchase(db, purchase)
            self._expire(db, row["household"])
            row = self._purchase(db, purchase)
            if row["state"] == "expired":
                failure = Rejection("approval_expired", "Checkout expired. Submit a fresh proposal.")
            else:
                self._check_cart(row, current_cart)
                if row["state"] not in ("reserved", "approved"):
                    raise Rejection("invalid_state", "Purchase is not awaiting owner approval.")
                if row["state"] == "reserved":
                    payload = {"purchase": purchase, "household": row["household"],
                               "agent": row["agent"], "cart_hash": row["cart_hash"],
                               "amount_cents": row["amount_cents"], "currency": "USD",
                               "expires_at": row["expires_at"],
                               "policy_version": row["policy_version"]}
                    permit = self._sign(payload)
                    db.execute("UPDATE purchases SET state='approved',permit=? WHERE id=?",
                               (permit, purchase))
                    self._event(db, purchase, "approved", cart_hash=row["cart_hash"])
                row = self._purchase(db, purchase)
                result = {**self._public(row), "permit": row["permit"]}
        if failure:
            raise failure
        return result

    def release(self, purchase: str):
        with self._transaction() as db:
            row = self._purchase(db, purchase)
            if row["state"] in ("reserved", "approved"):
                db.execute("UPDATE purchases SET state='released' WHERE id=?", (purchase,))
                self._event(db, purchase, "released")
            elif row["state"] not in ("released", "expired"):
                raise Rejection("payment_may_exist", "Reconcile or void the payment before releasing budget.")
            self._summary(db, row["household"])
            return self._public(self._purchase(db, purchase))

    def begin_payment(self, purchase: str, action: str, permit: str, current_cart: Cart):
        if action not in PAYMENT_STARTS:
            raise Rejection("invalid_action", "Unknown payment action.")
        failure = None
        result = None
        with self._transaction() as db:
            row = self._purchase(db, purchase)
            self._expire(db, row["household"])
            row = self._purchase(db, purchase)
            self._check_permit(row, permit)
            self._check_cart(row, current_cart)
            previous = db.execute("SELECT * FROM operations WHERE purchase=? AND action=?",
                                  (purchase, action)).fetchone()
            if previous:
                if previous["state"] == "completed":
                    result = {"execute": False, "operation_id": previous["id"],
                              "result": json.loads(previous["result_json"])}
                else:
                    failure = Rejection("reconcile_required", "An operation already started; refresh payment status.",
                                        operation_id=previous["id"])
            elif action == "authorize" and row["state"] == "expired":
                failure = Rejection("approval_expired", "Checkout expired before payment authorization started.")
            else:
                source, destination = PAYMENT_STARTS[action]
                if row["state"] != source:
                    raise Rejection("invalid_state", f"Cannot {action} a purchase in state {row['state']}.")
                if action in ("capture", "void") and not row["authorization_id"]:
                    raise Rejection("missing_authorization", "PayPal authorization is required.")
                if action == "authorize" and row["permit_consumed_at"] is not None:
                    raise Rejection("approval_consumed", "This consent already initiated a payment lifecycle.")
                operation = str(uuid.uuid4())
                intent = {"purchase": purchase, "action": action,
                          "cart_hash": row["cart_hash"], "cart": json.loads(row["cart_json"]),
                          "amount_cents": row["amount_cents"], "currency": "USD",
                          "order_id": row["order_id"], "authorization_id": row["authorization_id"]}
                db.execute("INSERT INTO operations(id,purchase,action,state,intent_json) VALUES(?,?,?,'started',?)",
                           (operation, purchase, action, canonical(intent)))
                if action == "authorize":
                    db.execute("UPDATE purchases SET permit_consumed_at=? WHERE id=?", (self.now(), purchase))
                db.execute("UPDATE purchases SET state=? WHERE id=?", (destination, purchase))
                self._event(db, purchase, destination, operation_id=operation)
                self._summary(db, row["household"])
                result = {"execute": True, "operation_id": operation,
                          "purchase": self._public(self._purchase(db, purchase))}
        if failure:
            raise failure
        return result

    def finish_payment(self, operation: str, *, outcome: str, order_id: str | None = None,
                       authorization_id: str | None = None, capture_id: str | None = None):
        """Trusted adapter only. 'unknown' retains budget until verified reconciliation.

        Reconciliation calls this again on the same operation with verified success.
        Definite errors are conservatively kept pending in this first prototype.
        """
        if outcome not in ("success", "unknown"):
            raise Rejection("invalid_outcome", "Use verified success or unknown.")
        with self._transaction() as db:
            op = db.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
            if not op:
                raise Rejection("unknown_operation", "Operation does not exist.")
            if op["state"] == "completed":
                return json.loads(op["result_json"])
            row = self._purchase(db, op["purchase"])
            if outcome == "unknown":
                db.execute("UPDATE purchases SET state='reconcile_pending' WHERE id=?", (row["id"],))
                self._event(db, row["id"], "reconcile_pending", operation_id=operation)
                return self._public(self._purchase(db, row["id"]))
            action = op["action"]
            if action == "authorize":
                if not order_id or not authorization_id:
                    raise Rejection("invalid_payment_result", "Authorization needs order and authorization IDs.")
                if row["order_id"] and row["order_id"] != order_id:
                    raise Rejection("order_changed", "Payment response does not match the bound order.")
                db.execute("UPDATE purchases SET order_id=?,authorization_id=? WHERE id=?",
                           (order_id, authorization_id, row["id"]))
            if action == "capture":
                if not capture_id:
                    raise Rejection("invalid_payment_result", "Capture ID is required.")
                db.execute("UPDATE purchases SET capture_id=? WHERE id=?", (capture_id, row["id"]))
            destination = PAYMENT_ENDS[action]
            db.execute("UPDATE purchases SET state=? WHERE id=?", (destination, row["id"]))
            self._event(db, row["id"], destination, operation_id=operation)
            result = self._public(self._purchase(db, row["id"]))
            db.execute("UPDATE operations SET state='completed',result_json=? WHERE id=?",
                       (canonical(result), operation))
            self._summary(db, row["household"])
            return result

    def bind_order(self, purchase: str, order_id: str):
        with self._transaction() as db:
            row = self._purchase(db, purchase)
            if row["state"] != "approved":
                raise Rejection("invalid_state", "Only approved purchases can have a checkout order.")
            if row["order_id"]:
                if row["order_id"] != order_id:
                    raise Rejection("order_changed", "A different order is already bound.")
                return self._public(row)
            db.execute("UPDATE purchases SET order_id=? WHERE id=?", (order_id, purchase))
            self._event(db, purchase, "order_bound", order_id=order_id)
            return self._public(self._purchase(db, purchase))

    @staticmethod
    def _public(row) -> dict:
        return {k: row[k] for k in ("id", "household", "agent", "cart_hash", "amount_cents",
                                   "state", "expires_at", "policy_version", "order_id",
                                   "authorization_id", "capture_id")}

    def get(self, purchase: str):
        with self._transaction() as db:
            row = self._purchase(db, purchase)
            self._expire(db, row["household"])
            row = self._purchase(db, purchase)
            return {**self._public(row), "cart": json.loads(row["cart_json"])}

    def audit(self, purchase: str):
        with self._transaction() as db:
            self._purchase(db, purchase)
            return [{"sequence": r["sequence"], "at": r["at"], "event": r["event"],
                     "details": json.loads(r["details_json"])} for r in db.execute(
                         "SELECT * FROM events WHERE purchase=? ORDER BY sequence", (purchase,))]

    def operation(self, operation: str):
        with self._transaction() as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
            if not row:
                raise Rejection("unknown_operation", "Operation does not exist.")
            return dict(row)
