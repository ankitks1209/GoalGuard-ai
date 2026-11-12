# PayPal sandbox setup

The developer dashboard uses your normal PayPal login. Checkout uses separate
sandbox seller/buyer identities and test funds. Never use live credentials.

## 1. Create sandbox accounts

Sign in to the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/).
Under **Testing Tools → Sandbox Accounts**, locate or create a Business seller
and a Personal buyer. Navigation labels can differ between dashboard versions.
For the USD prototype, use compatible sandbox profiles and ensure the buyer has
USD test funds. Sandbox profiles do not change your real account's country.

Keep the generated emails/passwords private. Buyer passwords do not belong in
GoalGuard configuration, logs or the repository. An observed IN buyer/seller
checkout displayed a currency error; a US buyer in a fresh browser session later
succeeded with the same IN seller. Those changes were not isolated, so the exact
earlier cause remains unconfirmed.

If sandbox checkout reports `UNSUPPORTED_PAYEE_CURRENCY`, check the seller
linked to the app and its USD receiving preferences. For the next test, use a
US Personal sandbox buyer with test funds in a separate browser session. If the
seller cannot receive USD, configure a USD-capable Business sandbox seller and
use the REST app credentials and merchant ID for that same account. The
[November 3 run](../reports/combined-demo-2026-11-03.json) reached order creation
before this error stopped buyer checkout.
[PayPal currency settings](https://developer.paypal.com/api/codes/currency)

## 2. Create an app

Under **Apps & Credentials**, select **Sandbox → Create App**. Name the app
GoalGuard and attach it to the Business sandbox seller. If an app type is offered,
choose Merchant. Copy its Client ID and Secret privately.

The current adapter explicitly sets and validates `payee.merchant_id`, so also
obtain the merchant ID for the same Business sandbox account. Check its account
details first. If not displayed, sign into [PayPal sandbox](https://www.sandbox.paypal.com/)
with that seller's generated credentials, then find Business information in
Account Settings. The merchant ID differs from the email and REST Client ID.

## 3. Configure the checkout

If you need to create the configuration file, run this from the repository root:

```sh
cp .env.example .env
```

Fill only these entries with your own sandbox values:

```dotenv
PAYPAL_SANDBOX_CLIENT_ID=
PAYPAL_SANDBOX_CLIENT_SECRET=
PAYPAL_SANDBOX_MERCHANT_ID=
```

Keep the return/cancel settings from the example unless your local integration
requires different URLs. Environment variables take precedence over `.env`.
The parser reads values without executing shell expressions. No access token,
buyer password, webhook ID or live payment credential is required in this file.

Start the API with the configured file and an external persistent state directory
as described in [Getting started](getting-started.md).

## 4. Complete an owner-approved purchase

1. Preview and confirm a financial plan with the owner token.
2. Propose catalog items with an agent token.
3. Review and approve the exact cart hash with the owner token; retain its permit
   in the owner workflow, never the agent context.
4. Create checkout and open the returned PayPal approval URL. Sign in and approve
   manually using the separate Personal sandbox buyer.
5. Authorize through the owner API after PayPal order status is `APPROVED`.
6. For simulated merchant fulfilment, capture the exact approved amount. To cancel
   an uncaptured authorization, void it instead and verify provider status.
7. If a response is unavailable, keep the obligation and use status refresh.

In the browser, open **Purchases**, approve the exact cart, and create the
sandbox checkout. After buyer approval, return to the same workspace and choose
**Verify buyer approval and authorize**. For a local walkthrough, configure the
return and cancel URLs to the running workspace root. The gateway checks the
provider order and validates merchant, cart and amount before authorization.
An order marked `COMPLETED` can still contain only an authorization. Confirm
capture separately from the Payments resource and ledger.

See [API](api.md), [evaluation](evaluation.md), [PayPal REST setup](https://developer.paypal.com/api/get-started/)
and [sandbox account documentation](https://developer.paypal.com/sandbox-testing/accounts).
