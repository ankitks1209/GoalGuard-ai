# Security policy

## Supported use

GoalGuard is an alpha prototype for local development and PayPal sandbox use.
It is not ready for real-money use or public hosting. No release currently has
production security support.

The API binds to loopback and uses scoped local bearer tokens. The owner browser
exchanges its development token for a fixed 30-minute in-memory session with an
HttpOnly, SameSite=Strict cookie, session-bound CSRF and expected Origin/Host checks.
Owner credentials and signed consent permits belong only in the trusted owner
workflow. Production authentication and public-hosting security remain unfinished.

## Reporting a vulnerability

Use the repository's [private vulnerability reporting](https://github.com/ankitks1209/GoalGuard-ai/security/advisories/new)
if it is available. Private reporting may require repository-owner enablement.
If it is unavailable, open a minimal issue requesting a private contact channel;
omit exploit details, credentials and personal or financial data.
No response-time commitment is currently offered.

## Authority boundaries

- Agents propose catalog items and quantities. They cannot approve purchases or
  call payment endpoints with agent credentials.
- The server computes prices and checks protected commitments. The model has no
  authority to change accounting, grant consent or release an uncertain payment.
- Owner consent binds the exact cart, amount, currency and policy version.
- A durable intent precedes authorization, capture or void. An unknown outcome
  retains the reservation until provider status is verified.
- PayPal credentials remain server-side. Tokens, signing keys and databases are
  excluded from source control; runtime state is stored outside the checkout.

## Known limits

The owner token is a development mechanism, not production authentication.
Financial inputs and external cash events are self-reported. Proposal outcomes
and coarse counteroffers can reveal partial spending capacity, including through
colluding agent identities. Quotas reduce probing but do not guarantee privacy.
The fixed catalog does not establish safety for arbitrary retailer content.
Finite tests do not prove general resistance to attacks.

See [architecture](docs/architecture.md) and [evaluation](docs/evaluation.md) for
the implemented controls, evidence and unverified behavior.
