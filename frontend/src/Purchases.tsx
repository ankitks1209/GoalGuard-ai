import { useEffect, useRef, useState } from 'react';
import type { OwnerApi } from './api';
import type { Overview, Purchase } from './types';
import { money } from './types';

const pendingStates = new Set(['authorizing', 'capturing', 'voiding', 'reconcile_pending']);
export function Purchases({ api, overview, reading, version, onRefresh }: { api: OwnerApi; overview: Overview | null; reading: boolean; version: string; onRefresh: () => Promise<void> }) {
  const [consent, setConsent] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [links, setLinks] = useState<Record<string, string>>({});
  const running = useRef(false);
  const generation = useRef(0);
  useEffect(() => { generation.current++; setConsent({}); setLinks({}); setError(''); setMessage(''); }, [version]);
  async function action(purchase: Purchase, name: string) {
    if (running.current || !version) return;
    running.current = true; setBusy(purchase.id); setError(''); setMessage('');
    const current = generation.current;
    const body = name === 'approve' ? { cart_hash: purchase.cart_hash } : name === 'refresh'
      ? { operation_id: purchase.operation_id } : ['authorize', 'capture', 'void'].includes(name) ? { permit: purchase.permit } : {};
    try {
      const response = await api.request<{ approval_url?: string }>(`/v1/purchases/${encodeURIComponent(purchase.id)}/${name}`, body);
      if (current !== generation.current) return;
      if (response.approval_url) {
        const url = new URL(response.approval_url);
        if (url.origin !== 'https://www.sandbox.paypal.com') throw new Error('An unexpected checkout destination was returned. Refresh status before continuing.');
        setLinks(known => ({ ...known, [purchase.id]: url.href }));
      }
      setConsent(known => ({ ...known, [purchase.id]: '' }));
      setMessage('Request completed. Review the refreshed purchase status before the next step.');
      await onRefresh();
    } catch (caught) {
      if (current === generation.current) {
        setError((caught as Error).message + ' Refresh workspace status before any deliberate retry.');
        setConsent(known => ({ ...known, [purchase.id]: '' }));
        await onRefresh();
      }
    } finally { running.current = false; setBusy(''); }
  }
  return <section className="purchases" aria-label="Purchase requests">
    <header className="page-heading">
      <h1>Purchase requests</h1>
      <p className="muted">Every cart has its own consent. A reservation is a budget commitment, not a PayPal hold.</p>
      <div className="purchase-toolbar">
        <span className="status-label">{overview ? `${overview.purchases.length} ${overview.purchases.length === 1 ? 'request' : 'requests'}` : 'Request count unavailable'}</span>
        <div className="actions"><button onClick={() => void onRefresh()}>Refresh workspace</button><small>Reads current status. No payment retries.</small></div>
      </div>
    </header>
    {error && <p className="notice" role="alert">{error}</p>}{message && <p className="notice" role="status">{message}</p>}
    {reading && <p role="status">{overview ? 'Refreshing purchase requests…' : 'Loading purchase requests…'}</p>}
    {!overview && !reading && <p className="notice">Purchase requests are unavailable. Refresh workspace to read current status.</p>}
    {overview && !overview.purchases.length && <div className="empty-state"><h2>No purchase requests yet</h2><p>After you confirm a plan, scoped shopping agents can submit synthetic catalog proposals.</p></div>}
    {overview?.purchases.map(purchase => {
      const pending = pendingStates.has(purchase.state);
      const signature = `${purchase.cart_hash}:${purchase.amount_cents}:${purchase.expires_at}`;
      const approved = consent[purchase.id] === signature;
      const expired = Date.now() / 1000 >= purchase.expires_at;
      const button = (name: string, label: string, disabled = false) => <button disabled={!!busy || disabled || !version} onClick={() => void action(purchase, name)}>{label}</button>;
      return <article className="purchase-card purchase-review-grid" aria-label={`Purchase ${purchase.id}`} key={purchase.id}>
        <div className="purchase-cart">
          <h2 id={`purchase-heading-${purchase.id}`} tabIndex={-1}>{purchase.agent}</h2><p className="muted">{purchase.cart.merchant}</p>
          <table><caption className="muted">Exact cart · {purchase.cart.currency}</caption><thead><tr><th scope="col">Item</th><th scope="col">Qty</th><th scope="col">Unit price</th><th scope="col">Line total</th></tr></thead><tbody>{purchase.cart.items.map(item => <tr key={item.sku}><td>{item.sku}</td><td>{item.quantity}</td><td>{money(item.unit_cents)}</td><td>{money(item.unit_cents * item.quantity)}</td></tr>)}</tbody></table>
          <div className="details-row"><span>Shipping</span><span>{money(purchase.cart.shipping_cents)}</span></div><div className="details-row"><span>Tax</span><span>{money(purchase.cart.tax_cents)}</span></div>
          <p className="purchase-id">Purchase {purchase.id}</p>
        </div>
        <div className="purchase-decision">
          <p className="status-label">{purchase.state.replaceAll('_', ' ')}</p>
          <p className="purchase-total">{money(purchase.amount_cents)} <small>{purchase.cart.currency} total</small></p>
          {['reserved', 'approved'].includes(purchase.state) && <p className="muted">Budget reservation deadline:<br />{new Date(purchase.expires_at * 1000).toLocaleString()}.</p>}
          {purchase.state === 'reserved' && <><label className="checkbox-label"><input type="checkbox" checked={approved} disabled={!!busy || expired} onChange={event => setConsent(known => ({ ...known, [purchase.id]: event.target.checked ? signature : '' }))} />I approve these exact items and the {money(purchase.amount_cents)} total.</label><div className="actions">{button('approve', 'Approve exact cart', !approved || expired)}{button('release', 'Release reservation')}</div></>}
          {purchase.state === 'approved' && <><p>Owner consent recorded. Buyer approval on PayPal is a separate step.</p><div className="actions">{button('checkout', 'Create sandbox checkout', expired)}{purchase.order_id && button('authorize', 'Verify buyer approval and authorize', !purchase.permit || expired)}{button('release', 'Release reservation')}</div></>}
          {['reserved', 'approved'].includes(purchase.state) && <p className="muted purchase-consent-note">Consent applies only to this exact cart and total.{purchase.state === 'reserved' && ' Buyer approval on PayPal is a separate step.'}</p>}
          {links[purchase.id] && <p><a className="checkout-link" href={links[purchase.id]} target="_blank" rel="noreferrer">Continue to PayPal sandbox ↗</a><br /><small>After buyer approval, return here and choose “Verify buyer approval and authorize”. A redirect alone proves nothing.</small></p>}
          {purchase.state === 'authorized' && <><p>PayPal authorization verified. Capture only after manual demo fulfilment.</p><label className="checkbox-label"><input type="checkbox" checked={approved} disabled={!!busy} onChange={event => setConsent(known => ({ ...known, [purchase.id]: event.target.checked ? signature : '' }))} />I confirm manual demo fulfilment is complete.</label><div className="actions">{button('capture', 'Capture after manual fulfilment', !approved || !purchase.permit)}{button('void', 'Void authorization', !purchase.permit)}</div></>}
          {pending && <p className="notice">Payment outcome is pending. Budget remains committed. Do not repeat a payment action; refresh its existing operation status.</p>}
          {pending && purchase.operation_id && <div className="actions">{button('refresh', 'Refresh payment status')}</div>}
          {purchase.state === 'captured' && <p>Captured spending stays deducted. Fulfilment is a manual demo action.</p>}
          {['released', 'expired', 'voided'].includes(purchase.state) && <p className="muted">This request is closed. A new cart needs a fresh agent proposal.</p>}
          {busy === purchase.id && <p role="status">Request in progress. Please wait; do not resubmit.</p>}
        </div>
      </article>;
    })}
  </section>;
}
