"""Read an explicit local env file without shell expansion or secret logging."""

import os
from pathlib import Path


SANDBOX_KEYS = (
    "PAYPAL_SANDBOX_CLIENT_ID", "PAYPAL_SANDBOX_CLIENT_SECRET",
    "PAYPAL_SANDBOX_MERCHANT_ID", "PAYPAL_RETURN_URL", "PAYPAL_CANCEL_URL",
)


def sandbox_config(path: Path) -> dict:
    values = {}
    if path.exists():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or key.strip() not in SANDBOX_KEYS:
                raise ValueError(f"Unsupported configuration entry on line {number}; values were not logged.")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            values[key.strip()] = value
    return {key: os.environ.get(key) or values.get(key, "") for key in SANDBOX_KEYS}
