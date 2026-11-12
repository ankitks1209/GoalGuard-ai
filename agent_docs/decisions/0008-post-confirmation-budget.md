# 0008: Show the budget after plan confirmation

Date: 2026-11-01. Status: accepted by the owner.

The setup form remained open after confirmation, leaving the owner below the
budget summary. The owner asked to see the budget directly after confirming.

After the exact-plan confirmation succeeds, read the overview. Only a successful
read containing a plan in the same owner session switches to Budget, collapses
setup and focuses/reveals the budget heading without animation. Show confirmed
protections and forecast separately. Keep an explicit “Edit plan” action and the
existing financial-update disclosure. Reopening the editor retains its terms and
requires another deliberate preview and confirmation for revisions or rollover.

The transition is an in-memory response to confirmation. It does not introduce a
route, persistent browser storage, new service or payment/ledger change. Reopening
the application retains the existing setup behavior. Read failures leave recovery
visible; session expiry locks the workspace. Neither automatically retries a write.

Verification uses component tests for success, delayed/missing/failed reads,
expiry and rejected confirmation, plus synthetic browser checks at desktop and
phone widths. These are not live model or PayPal evidence.
