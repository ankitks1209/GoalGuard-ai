# 0006 — Reveal plan details progressively

Status: owner selected A, essentials first (23 October 2026).

The owner found the first budget form too demanding. Show cash, buffer, next
payday and expected income first, with bills, savings and plan metadata in
expandable sections. This changes presentation, not financial requirements.

Closing a section must retain every value and include it in the exact preview.
Never infer or omit bills, savings or timezone because their fields are hidden.
Required fields reveal their section on validation failure; native automatic
reveal did not work in the observed Chromium test. Preview and separate owner
confirmation remain mandatory. Existing sessions and payment controls stay intact.

No wizard, model processing, new financial defaults or dependencies were added.
The wordmark is a separate pending owner choice; prototypes do not authorize it.
