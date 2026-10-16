# GoalGuard: PayPal sandbox setup

The developer dashboard uses your normal PayPal login. Payments in our demo use
separate sandbox buyer and seller accounts and test funds.

## 1. Sign in to the developer dashboard

Open https://developer.paypal.com/dashboard/ and log in. If you have no PayPal
account, complete Sign Up yourself using your actual country and details.
PayPal documents a Business-account requirement for testing integrations outside
the US; if signup or developer access asks for business verification, follow the
actual account requirements rather than inventing business details.

## 2. Locate the sandbox buyer and seller

Open **Testing Tools → Sandbox Accounts** (some navigation versions say
**Sandbox → Accounts**). PayPal normally provides a Business seller and a Personal
buyer. If needed, choose **Create Account** and create one of each. For our USD
prototype, US sandbox profiles are suitable; these are test profiles, not your
real PayPal account's country settings. Verify USD is available on both.

For each account, open **⋮ → View/Edit Account** and note its generated email and
password privately. The buyer needs test funds available for checkout. Do not put
these passwords into the project .env or chat.

## 3. Create the app and get its credentials

Open **Apps & Credentials**, select **Sandbox**, then **Create App**.

- App name: **GoalGuard**.
- App type: **Merchant**, if shown.
- Sandbox business account: select the seller from step 2.

Create the app. Its details page shows **Client ID** and **Secret** (reveal the
secret if needed). Copy them into the corresponding local configuration entries.
Keep the seller account selected here consistent with the merchant ID below.

## 4. Find the sandbox merchant ID

GoalGuard's current adapter explicitly sets the order payee and validates the
merchant ID on returned orders, so this value is required for this implementation.
First check the matching Business sandbox account's View/Edit details for a
displayed merchant ID. If available, copy it without another login. Otherwise:

Open https://www.sandbox.paypal.com/signin/ in a separate browser session or
private window. Sign in with the **Business sandbox seller's generated email and
password**, not your normal developer-dashboard login or the buyer account.

Open **Account Settings → Business profile → Business information**. Copy the
value next to **PayPal Merchant ID**. This is neither the account email nor the
REST app's Client ID.

## 5. Save the three values locally

Open the existing file:

`/Users/golukakarot/Developer/Projects/GoalGuard-ai/.env`

Fill only these blank entries, replacing the example text below:

```dotenv
PAYPAL_SANDBOX_CLIENT_ID=your_client_id
PAYPAL_SANDBOX_CLIENT_SECRET=your_client_secret
PAYPAL_SANDBOX_MERCHANT_ID=your_sandbox_seller_merchant_id
```

Keep the existing return and cancel URLs. They are application settings, not
credentials supplied by PayPal. No access token, webhook ID, buyer password or
live payment credential is needed in this file. Save it and tell Codex
**"Sandbox configured."** Keep credentials out of chat and screenshots.

The existing callback URLs are placeholders: until the owner interface is built,
buyer approval verification returns to the API workflow. Saving credentials does
not itself prove payment success; the next gate exercises actual sandbox
authorize/capture and authorize/void with the Personal sandbox buyer.

## Official references

- [REST app credentials and sandbox logins](https://developer.paypal.com/api/get-started/)
- [Sandbox account creation](https://developer.paypal.com/sandbox-testing/accounts)
- [Finding the merchant ID](https://www.paypal.com/us/cshelp/article/how-do-i-find-my-secure-merchant-id-on-my-paypal-account-help538)
