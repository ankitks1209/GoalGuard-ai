"""Subprocess fixture: persist a simulated provider result, then await test kill."""

import json
from pathlib import Path
import sys
import time

from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway, Principal
from tests.test_gateway import FakePayPal


class CrashPayPal(FakePayPal):
    def __init__(self, fixture_path, marker_path, action):
        super().__init__()
        self.fixture_path = fixture_path
        self.marker_path = marker_path
        self.action = action
        data = json.loads(fixture_path.read_text())
        self.order = data["order"]
        self.authorization = data["authorization"]

    def _request(self, method, path, body=None, request_id=None):
        response = super()._request(method, path, body, request_id)
        if method == "POST" and path.endswith("/" + self.action):
            # Provider state survives independently from the GoalGuard DB.
            self.fixture_path.write_text(json.dumps({"order": self.order,
                                                     "authorization": self.authorization,
                                                     "request_id": request_id}))
            self.marker_path.write_text("provider action recorded; ledger completion not written")
            while True:
                time.sleep(0.05)
        return response


if __name__ == "__main__":
    directory = Path(sys.argv[1])
    request = json.loads((directory / "request.json").read_text())
    ledger = Ledger(directory / "ledger.sqlite")
    paypal = CrashPayPal(directory / "provider.json", directory / "ready", request["action"])
    gateway = Gateway(ledger, Catalog(), paypal)
    gateway.execute(Principal("demo-home", "owner", "owner"), request["purchase"],
                    request["action"], request["permit"])
