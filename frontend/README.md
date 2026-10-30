# Owner workspace

The React/TypeScript/Vite interface connects three screens: plan setup with
preview/confirmation, exact-cart purchase review, and the timeline. Budget also
includes optional sample-only AI drafting and paired financial-activity records.
It uses the Python API on the same origin, with ephemeral unlocking, logout,
30-minute expiry, in-memory form retention and deliberate mutation retries.
No owner key or consent permit is persisted in browser storage.

From the repository root with Node 24 and the Python virtual environment:

```sh
npm --prefix frontend ci
npm --prefix frontend run build
python server.py
```

Open the printed loopback URL and unlock with the local owner token from your
private runtime state. Keep that key outside model context. The server serves
built assets only; the Vite dev server on port 5173 has no owner-API proxy.
This interface is for local development, synthetic catalog items, manual
fulfilment and the PayPal sandbox. Public hosting remains out of scope.

Current checks pass 52 frontend tests, lint, explicit typecheck, all coverage
floors and build. Tests cover session handling, stale replies, manual plan
preview/confirmation, exact consent, uncertain-payment refresh and timeline
states. Browser inspection used a disposable synthetic household and verified
unlocking, keyboard exact-cart approval and its timeline event at the available
compact viewport. No model or payment provider was configured in that inspection.
A complete new provider demonstration, native accessibility review, Firefox and
Linux/hosted verification remain pending. Automated desktop/mobile rendering and
an actual local HTTP/session/CSRF/ledger walkthrough used only synthetic data and
simulated extraction. See [owner-form verification](../agent_docs/owner-form-verification.md).

Before confirming an initial plan, open “Try AI drafting with sample data”. Its
fixed read-only sample requires explicit consent; existing records and manual
entries are excluded. Missing facts/provider failures retain manual entry.
Review the extracted amounts/dates and separately confirm the exact preview.

With an active plan, open “Record a financial update” for received income, paid
bills, savings deposits, other cash changes and received refunds. Select the
existing linked record where required, review and confirm activity already
completed externally. A lost response freezes its terms and ID: read recorded
status, then deliberately retry the same ID only if needed. Nothing retries on
unlock. After reload, inspect Timeline's amounts/reference/record IDs before
recording again; pending forms are not persisted in browser storage.

The accepted light dashboard/session design is recorded in
[ADR 0004](../agent_docs/decisions/0004-owner-interface-proposal.md).
No frontend dependencies changed in this implementation.

## Installation

Use Node 24 and npm. From the repository root:

```sh
npm --prefix frontend ci
npm --prefix frontend run check
```

The first owner-Terminal install generated the actual `package-lock.json`.
Direct dependency versions are explicit. Vite's official React-TS template,
Vitest 4.1.0's declared Vite peer range and Testing Library's React 19 peer range
were inspected on 21 October 2026. The owner's install and lint/typecheck/three
initial smoke tests/build passed. After the React test setup fix, the builder
also ran all checks successfully: four tests and 100% statement/branch/function/
line coverage of the two scaffold source files. A fresh `npm ci` and remote Linux
CI run have not yet been observed.
If installation fails, retain the error; do not use `--force` or `--legacy-peer-deps`.
Do not rerun with an arbitrary new toolchain just to remove a peer error.

Keep the generated lockfile with the manifest when publication is authorized.
Use `npm --prefix frontend ci` in fresh checkouts and CI. The installed tree's
manifest/lock consistency has been inspected; clean reinstall and hosted CI remain
separate checks.

The owner audit identifies **three moderate findings from one underlying advisory**:
[GHSA-82fw-gwwq-j7x9](https://github.com/advisories/GHSA-82fw-gwwq-j7x9), affecting
`@vitest/mocker` and propagated through Vitest/coverage. The advisory's first
patched stable version is 4.1.11; [4.1.12](https://github.com/vitest-dev/vitest/releases/tag/v4.1.12)
also adds follow-up mock hardening. The targeted update is **4.1.12 for both
`vitest` and `@vitest/coverage-v8`**. The builder's initial update was blocked by
DNS resolution. On 22 October the owner completed the targeted install; the
manifest, generated lock and installed Vitest/coverage/mocker now match 4.1.12.
The install's audit reported **135 packages audited, zero vulnerabilities**.
The owner and builder both ran the six-test full check successfully afterward.
This records the install-time audit result, not an independent later registry
audit or a guarantee that no future advisories exist.

The two new regressions reject stale manifest/lock and installed tooling; they do
not reproduce the exploit or replace registry audits. Never fabricate
lockfile integrity entries or run `npm audit fix --force`. After a registry DNS
failure, use the owner's Terminal rather than retrying blindly or deleting the
working dependency tree with `npm ci` in a network-blocked environment.

## Checks and boundaries

- `npm --prefix frontend run lint`: Oxlint, with warnings rejected.
- `npm --prefix frontend run typecheck`: explicit TypeScript no-emit check.
- `npm --prefix frontend test`: Vitest component tests with a simulated DOM.
- `npm --prefix frontend run test:coverage`: V8 coverage, 80% for statements,
  branches, functions and lines; includes unimported application source. Reports
  stay under the ignored `.local/checks/frontend-coverage/` directory.
- `npm --prefix frontend run build`: typecheck then Vite static build.
- `npm --prefix frontend run check`: all four gates sequentially.

The checks and synthetic browser inspection do not establish real payment
behavior or a complete hackathon demo. Future behavior requires focused failing
tests and appropriate browser inspection.
Keep the existing Python coverage gate; frontend coverage is a separate measure.

The `Frontend Node 24` workflow job installs using the lockfile and runs `check`.
The local `goalguard-frontend` pre-commit hook runs that same command. Existing
Python gates remain active. Workflow/hook configuration does not establish a
hosted CI pass or GitHub-required checks; those still need publication and remote
configuration. The registry audit is not part of `check`; the advisory-specific
version regressions are, and now pass against the patched installed tooling.

## macOS install-script notice

Npm also printed an unreviewed-script notice for `fsevents@2.3.3`. The lockfile
identifies it as Vite's optional macOS file-watching dependency. This is separate
from the cleared vulnerability finding. No `allowScripts` policy or script approval
was changed; test/build gates pass in the existing installation. Native watch-mode
behavior has not been verified. Do not approve all install scripts merely to
silence this notice. See [npm script-review behavior](https://docs.npmjs.com/cli/v11/commands/npm-approve-scripts/).

## Appearance-only development preview

`npm --prefix frontend run dev` listens on 127.0.0.1:5173. It has no API proxy,
so unlocking there reports a connection/response error. Use the Python-served
build above for the connected workspace. Never put owner keys, model keys or
PayPal credentials in frontend source, Vite variables, fixtures or URLs. Test
fixtures use synthetic keys with disposable state only.

References: [Vite React-TS template](https://github.com/vitejs/vite/blob/main/packages/create-vite/template-react-ts/package.json),
[Vitest 4.1.0](https://github.com/vitest-dev/vitest/blob/v4.1.0/packages/vitest/package.json),
[Testing Library](https://github.com/testing-library/react-testing-library/tree/v16.3.0),
[Vitest coverage](https://vitest.dev/guide/coverage.html).

## Design enforcement and first-screen review

Playwright/axe and Chromium are approved development tools. See
[synthetic browser checks](tests/browser/README.md) for commands, fixtures and
baseline review. `npm run lint` now includes `check:tokens`, which rejects raw
style values outside the canonical repository-root `src/styles/tokens.css`.
The approved first budget-screen migration replaces the old raw stylesheet and
repairs the observed contrast failures. Tokens are imported into the app;
Instrument Sans and its license are served locally. The owner must review the
first screen before further screen redesign. The new browser CI job and Linux
screenshot baselines remain unverified until run and reviewed on that platform.
