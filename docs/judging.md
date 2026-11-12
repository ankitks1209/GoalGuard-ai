# Try GoalGuard locally

This walkthrough uses the real owner interface, API and budget ledger with
synthetic data. A setup script confirms a sample plan and makes deterministic
proposals. The checkout provider and AI model are disabled.

### Start from the ZIP or build from source

If you have the judging ZIP, extract it and enter the extracted
`GoalGuard-judging` folder. The ZIP includes the built UI. Use Python 3.11 or
later with system time zone data, as on macOS and typical Linux desktops.

From the public source repository, clone the repo and build the UI with Node 24
and npm:

```sh
git clone https://github.com/ankitks1209/GoalGuard-ai.git
cd GoalGuard-ai
npm --prefix frontend ci
npm --prefix frontend run build
```

From either folder, start the demo:

```sh
python3 -m scripts.judging_demo
```

### Walk through owner consent

1. Open the printed localhost URL. Open the printed key file locally and copy
   the value named `owner` into **Owner key**, then select **Unlock workspace**.
   Keep the terminal running. The key is generated for this run; don't share it.
2. In **Budget**, see $600 cash, $250 protected for bills, buffer and savings,
   $320 reserved, $30 safely spendable and $0 captured. The $220 microphone was
   reserved first. The $180 vacuum exceeded what remained, so the fixture
   proposed the $100 compact vacuum after the gateway returned that alternative.
3. Choose **Review cart** on the $220 request and inspect the microphone.
   Tick the exact-cart consent checkbox and choose **Approve exact cart**. Consent leaves the amount reserved;
   it does not move money. Stop at owner approval. The interface has sandbox
   controls, but this launcher supplies no payment adapter.
4. Open **Timeline** and find the approval event. Stop the launcher with Ctrl-C
   to discard this synthetic household. If its 15-minute reservations expire,
   stop and restart the launcher to start a fresh synthetic walkthrough.

The ZIP demonstrates budget protection and owner consent. It provides no live
Gemini or PayPal evidence. The separately scoped combined provider demo remains
incomplete. For provider setup, see the repository's
[AI setup](https://github.com/ankitks1209/GoalGuard-ai/blob/main/docs/agents.md)
and [PayPal sandbox setup](https://github.com/ankitks1209/GoalGuard-ai/blob/main/docs/paypal-setup.md).
From a source checkout, `python3 demo.py` also demonstrates competing proposals
and recovery in the terminal.

To rebuild the ZIP from the source checkout, install the locked frontend tools
with `npm --prefix frontend ci` under Node 24, then run:

```sh
python3 scripts/build_judging_bundle.py dist/GoalGuard-judging.zip
```

The build includes the launcher, backend source, built UI and licenses. Runtime
state, credentials, environment files and private provider transcripts are
excluded. The output path must be new.
