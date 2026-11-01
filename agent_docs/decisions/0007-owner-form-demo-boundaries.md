# 0007 — Owner drafting and financial-record UI boundaries

Date: 28 October 2026. Status: accepted scope; implementation verified separately.

The owner requested the remaining owner forms and explicitly chose
synthetic/sample text only for AI drafting. AGENTS continues to prohibit model
access to private financial records, credentials and payment authority.

The browser's initial-plan AI path sends only its displayed built-in sample,
after consent. It accepts no editable personal financial text and includes no
existing plan or manual field values. The backend validates extraction and
computes the preview; the owner separately confirms exact terms. Manual entry
remains available. This grants no future real-record processing exception.

Financial activity uses the existing atomic cash-event API. The UI generates a
unique record ID, shows an exact review and requires confirmation that activity
already happened externally. A lost response freezes the terms/ID until a
manual audit read; only a deliberate same-ID retry is offered if no matching
record is found. Unlock never replays mutations. Known validation rejections
leave input correctable. No payment/provider operation is added.

Pending details stay in memory, matching the existing session/form contract.
Reload does not preserve a pending ID in browser storage. The UI warns owners
to inspect Timeline first after reload; financial events now expose their
activity, amount, reference and ID there. Durable cross-reload pending-form
recovery would require separate scope. The approved design/tokens are reused;
no framework, dependency or service is added.
