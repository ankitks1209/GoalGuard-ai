"""Explicitly synthetic, fixed-price demo products; no real retailer claims."""

from itertools import product

from .ledger import Cart, Item, Rejection


PRODUCTS = {
    "mic-standard": {"name": "Demo USB microphone", "unit_cents": 22_000,
                     "need": "recording", "features": {"usb", "monitoring"}, "utility": 2,
                     "description": "Synthetic catalog item. USB and headphone monitoring."},
    "mic-budget": {"name": "Demo budget USB microphone", "unit_cents": 12_000,
                   "need": "recording", "features": {"usb", "monitoring"}, "utility": 1,
                   "description": "Synthetic catalog item. USB and headphone monitoring."},
    "vacuum-standard": {"name": "Demo vacuum cleaner", "unit_cents": 18_000,
                        "need": "cleaning", "features": {"floor"}, "utility": 2,
                        "description": "Synthetic catalog item. Floor cleaning."},
    "vacuum-budget": {"name": "Demo compact vacuum", "unit_cents": 10_000,
                      "need": "cleaning", "features": {"floor"}, "utility": 1,
                      "description": "Synthetic catalog item. Floor cleaning."},
}


class Catalog:
    def __init__(self, merchant="demo-merchant", products=None):
        self.merchant = merchant
        self.products = products if products is not None else PRODUCTS

    def quote(self, items: list[dict]) -> Cart:
        if not isinstance(items, list) or not items or len(items) > 10:
            raise Rejection("invalid_cart", "Provide one to ten SKU/quantity entries.")
        result = []
        for entry in items:
            if not isinstance(entry, dict) or set(entry) != {"sku", "quantity"}:
                raise Rejection("invalid_cart", "Agents may provide only SKU and quantity, never prices or approval flags.")
            sku = entry["sku"]
            if not isinstance(sku, str) or sku not in self.products:
                raise Rejection("unknown_product", "Product is not in the trusted demo catalog.")
            result.append(Item(sku, entry["quantity"], self.products[sku]["unit_cents"]))
        cart = Cart(self.merchant, tuple(result))
        cart.as_dict()
        return cart

    def alternatives(self, cart: Cart, available_cents: int) -> list[dict]:
        """Enumerate same-need, same-required-feature bundles in this tiny catalog.

        This is a deterministic fixture solver, not real-world suitability advice.
        """
        choices = []
        for item in cart.items:
            source = self.products[item.sku]
            choices.append([Item(sku, item.quantity, candidate["unit_cents"])
                            for sku, candidate in sorted(self.products.items())
                            if candidate["need"] == source["need"]
                            and source["features"] <= candidate["features"]])
        feasible = []
        for combination in product(*choices):
            candidate = Cart(cart.merchant, tuple(combination), cart.shipping_cents, cart.tax_cents)
            try:
                total = candidate.total_cents
            except Rejection:
                continue
            if total <= available_cents and candidate.cart_hash != cart.cart_hash:
                utility = sum(self.products[i.sku]["utility"] * i.quantity for i in combination)
                feasible.append((utility, total, candidate.as_dict()))
        feasible.sort(key=lambda value: (-value[0], value[1], str(value[2])))
        return [{"cart": candidate, "total_cents": total, "fixture_utility": utility,
                 "requires_new_proposal": True} for utility, total, candidate in feasible[:3]]

    def public(self):
        return [{"sku": sku, "name": p["name"], "unit_cents": p["unit_cents"],
                 "need": p["need"], "features": sorted(p["features"]),
                 "description": p["description"], "synthetic": True}
                for sku, p in sorted(self.products.items())]


def stored_cart(purchase: dict) -> Cart:
    data = purchase["cart"]
    return Cart(data["merchant"], tuple(Item(**i) for i in data["items"]),
                data["shipping_cents"], data["tax_cents"], data["currency"])
