/** Fixed synthetic facts only. Never interpolate owner input or stored records. */
export function sampleDraftText() {
  const today = new Date();
  const date = (days: number) => new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() + days)).toISOString().slice(0, 10);
  const deadline = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() + 2, 28)).toISOString().slice(0, 10);
  return `All amounts are USD. I have $600 current cash, excluding separately held savings, and want a $50 cash buffer. ` +
    `My next expected income is $400 on ${date(5)}. My only unpaid bill is Utilities, $100 due ${date(1)}. ` +
    `My savings goal is $600 by ${deadline}; $300 is already saved separately. Suggest a monthly contribution.`;
}
