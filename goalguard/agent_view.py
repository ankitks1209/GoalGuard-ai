"""Allowlisted agent responses. Owner financial records never cross this boundary."""

STATES = {"reserved", "approved", "authorizing", "authorized", "capturing", "voiding",
          "reconcile_pending", "captured", "released", "expired", "voided"}
REASONS = {"budget_exceeded", "proposal_limit", "forbidden", "unauthorized", "not_found",
           "invalid_body", "invalid_proposal", "invalid_cart", "invalid_request", "invalid_money",
           "unknown_product", "unknown_purchase", "unknown_operation", "unknown_household",
           "idempotency_conflict", "cart_changed", "invalid_state", "expired", "request_rejected",
           "internal_error", "payment_unavailable", "plan_required", "plan_not_ready", "policy_changed"}


def purchase_view(row):
    result = {key: row[key] for key in ("id", "cart_hash", "amount_cents", "expires_at") if key in row}
    result["state"] = row["state"] if row.get("state") in STATES else "reconcile_pending"
    return result


def offer_view(offer):
    return {"cart": {"items": [{"sku": item["sku"], "quantity": item["quantity"]}
                               for item in offer["cart"]["items"]]},
            "total_cents": offer["total_cents"], "requires_new_proposal": True}


def agent_view(payload):
    if "reason" in payload:
        result = {"decision": "denied", "reason": payload["reason"]
                  if payload["reason"] in REASONS else "request_rejected"}
        if result["reason"] == "budget_exceeded":
            result["counteroffers"] = [offer_view(o) for o in payload.get("counteroffers", [])[:1]]
        return result
    if "products" in payload:
        fields = ("sku", "name", "unit_cents", "need", "features", "description", "synthetic")
        return {"products": [{k: product[k] for k in fields if k in product}
                             for product in payload["products"]], "simulation": "synthetic_catalog"}
    if "headroom_floor_cents" in payload:
        return {"currency": "USD", "headroom_floor_cents": payload["headroom_floor_cents"]}
    if "purchase" in payload:
        row = purchase_view(payload["purchase"])
        return {"decision": row["state"], "purchase": row}
    if "id" in payload and "state" in payload:
        return purchase_view(payload)
    return {"decision": "denied", "reason": "request_rejected"}
