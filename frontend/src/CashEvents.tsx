import { useEffect, useRef, useState } from 'react';
import { ApiError } from './api';
import type { OwnerApi } from './api';
import type { Overview } from './types';
import { money } from './types';
import { parseMoney } from './moneyInput';

const activities = [
  ['income', 'Income received'], ['bill_payment', 'Bill paid'], ['savings_deposit', 'Savings deposited'],
  ['external_inflow', 'Other cash received'], ['external_outflow', 'Other cash spent'], ['refund', 'Refund received'],
];
interface RecordBody { event_id: string; kind: string; amount_cents: number; reference_id: string | null }
interface Review { body: RecordBody; label: string; referenceLabel: string }
export function CashEvents({ api, overview, version, disabled, onBusy, onInvalidate, onRefresh }: {
  api: OwnerApi; overview: Overview | null; version: string; disabled: boolean;
  onBusy: (value: boolean) => void; onInvalidate: () => void; onRefresh: () => Promise<void>;
}) {
  const [kind, setKind] = useState('');
  const [amount, setAmount] = useState('');
  const [reference, setReference] = useState('');
  const [review, setReview] = useState<Review | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [canRetry, setCanRetry] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const generation = useRef(0);
  const running = useRef(false);
  const attempted = useRef(false);
  useEffect(() => {
    generation.current++; setConsent(false); setError(''); setMessage(''); setCanRetry(false);
    if (attempted.current) setUncertain(true);
    else setReview(null);
    return () => { generation.current++; };
  }, [version]);

  const plan = overview?.plan;
  const referenceLabel = kind === 'bill_payment' ? 'Linked bill' : kind === 'savings_deposit' ? 'Linked savings goal'
    : kind === 'income' ? 'Linked expected income' : 'Linked captured purchase';
  const linked = ['bill_payment', 'savings_deposit', 'income', 'refund'].includes(kind);
  const options = !plan ? [] : kind === 'bill_payment' ? plan.spec.bills.map(bill => ({ id: bill.id, name: bill.name }))
    : kind === 'savings_deposit' ? (plan.spec.goal ? [{ id: plan.spec.goal.id, name: plan.spec.goal.title }] : [])
    : kind === 'income' ? (plan.spec.next_income ? [{ id: plan.spec.next_income.id, name: `${plan.spec.next_income.due_date} expected income` }] : [])
    : (overview?.purchases ?? []).filter(purchase => purchase.state === 'captured').map(purchase => ({ id: purchase.id, name: `${purchase.id} — ${money(purchase.amount_cents)}` }));

  function prepare() {
    setError(''); setMessage('');
    try {
      const cents = parseMoney(amount);
      if (!cents) throw new Error('Enter an amount greater than zero.');
      const label = activities.find(([value]) => value === kind)?.[1];
      if (!label) throw new Error('Choose the activity you have already completed.');
      const selected = options.find(option => option.id === reference);
      if (linked && !selected) throw new Error('Choose the matching linked record before reviewing.');
      setReview({ body: { event_id: crypto.randomUUID(), kind, amount_cents: cents, reference_id: linked ? reference : null },
        label, referenceLabel: selected?.name ?? 'No linked record' });
      setConsent(false); setUncertain(false); setCanRetry(false);
    } catch (caught) { setError((caught as Error).message); }
  }
  async function saved(already: boolean) {
    attempted.current = false; setReview(null); setConsent(false); setUncertain(false); setCanRetry(false); setAmount('');
    setMessage(already ? 'This update was already recorded. It has not been counted again.' : 'Financial update recorded. Review the refreshed budget and Timeline.');
    onInvalidate(); await onRefresh();
  }
  async function record() {
    if (running.current || disabled || !version || !review || !consent || (uncertain && !canRetry)) return;
    running.current = true; attempted.current = true; setBusy(true); onBusy(true); setError(''); setCanRetry(false); onInvalidate();
    const current = generation.current;
    try {
      const result = await api.request<{ recorded: boolean; event_id: string }>('/v1/plan/cash-events', review.body);
      if (current !== generation.current) return;
      if (typeof result.recorded !== 'boolean' || result.event_id !== review.body.event_id) throw new Error('The financial-record response was incomplete.');
      await saved(!result.recorded);
    } catch (caught) {
      if (current === generation.current) {
        setError((caught as Error).message);
        if (caught instanceof ApiError && caught.status === 409 && ['invalid_cash_event', 'invalid_money', 'invalid_request', 'plan_required'].includes(caught.reason)) {
          attempted.current = false; setReview(null); setConsent(false);
        } else setUncertain(true);
      }
    } finally { running.current = false; setBusy(false); onBusy(false); }
  }
  async function check() {
    if (running.current || !version || !review) return;
    running.current = true; setBusy(true); onBusy(true); setError(''); setCanRetry(false);
    const current = generation.current;
    try {
      const result = await api.request<{ events: { event: string; details: Record<string, unknown> }[] }>('/v1/plan/audit');
      if (current !== generation.current) return;
      if (!Array.isArray(result.events)) throw new Error('Recorded status is unavailable. Refresh again after checking the server.');
      const event = result.events.find(item => item.event === 'cash_recorded' && item.details?.event_id === review.body.event_id);
      if (event) {
        if (event.details.kind !== review.body.kind || event.details.amount_cents !== review.body.amount_cents || event.details.reference_id !== review.body.reference_id) {
          throw new Error('This record ID has different terms. Inspect Timeline before taking further action.');
        }
        await saved(true);
      } else { setCanRetry(true); setMessage('No matching record was found. You may deliberately retry these exact terms with the same record ID.'); await onRefresh(); }
    } catch (caught) { if (current === generation.current) setError((caught as Error).message); }
    finally { running.current = false; setBusy(false); onBusy(false); }
  }
  if (!plan) return null;
  return <details className="plan-section cash-events">
    <summary><span>Record a financial update</span><small className="section-hint">Income received, bills paid, savings deposited or cash corrections.</small></summary>
    <div className="section-content">
      <p>Record only activity that already happened outside GoalGuard. This does not pay a bill, transfer savings or issue a refund.</p>
      {error && <p className="notice" role="alert">{error}</p>}{message && <p className="notice" role="status">{message}</p>}
      <form onSubmit={event => { event.preventDefault(); prepare(); }}>
        <fieldset disabled={busy || disabled || !!review || !version}>
          <div className="form-grid">
            <div className="field"><label htmlFor="cash-kind">Activity</label><select id="cash-kind" value={kind} required onChange={event => { setKind(event.target.value); setReference(''); setError(''); }}>
              <option value="">Choose completed activity</option>{activities.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
            <div className="field"><label htmlFor="cash-amount">Amount (USD)</label><input id="cash-amount" value={amount} inputMode="decimal" required maxLength={40} onChange={event => setAmount(event.target.value)} /></div>
            {linked && <div className="field wide"><label htmlFor="cash-reference">{referenceLabel}</label><select id="cash-reference" required value={reference} onChange={event => setReference(event.target.value)}>
              <option value="">Choose the matching record</option>{options.map(option => <option key={option.id} value={option.id}>{option.name}</option>)}</select>
              {!options.length && <p className="muted">No matching record is available. {kind === 'refund' ? 'Only captured purchases can receive a recorded refund.' : 'Review your confirmed plan before recording this activity.'}</p>}</div>}
          </div>
          <div className="actions"><button type="submit" disabled={linked && !options.length}>Review update</button><small>Nothing is recorded until you confirm.</small></div>
        </fieldset>
      </form>
      {review && <section className="review" aria-labelledby="record-review-title">
        <h3 id="record-review-title">Review this financial record</h3>
        <dl><dt>Activity</dt><dd>{review.label}</dd><dt>Amount</dt><dd>{money(review.body.amount_cents)}</dd><dt>Linked record</dt><dd>{review.referenceLabel}</dd></dl>
        <p className="purchase-id">Record ID: {review.body.event_id}</p>
        <p className="notice">Recording changes your cash and any linked bill or savings protection together. Pre-payment reservations are released; started or uncertain payment obligations stay committed.</p>
        <label className="checkbox-label"><input type="checkbox" checked={consent} disabled={busy || !version} onChange={event => setConsent(event.target.checked)} />I confirm this already happened outside GoalGuard.</label>
        {uncertain ? <><p>Check whether this record was saved before retrying. Its terms and record ID remain unchanged. Keep this page open; after a reload, inspect Timeline before recording the activity again.</p><div className="actions">
          <button disabled={busy || !version} onClick={() => void check()}>Check recorded status</button>
          {canRetry && <button disabled={busy || !version || !consent} onClick={() => void record()}>Retry this same record</button>}
        </div></> : <div className="actions"><button className="primary" disabled={busy || disabled || !version || !consent} onClick={() => void record()}>Record this update</button>
          <button disabled={busy} onClick={() => { setReview(null); setConsent(false); }}>Edit this update</button></div>}
      </section>}
      {busy && <p role="status">Checking the financial record. Please wait; no action will retry automatically.</p>}
    </div>
  </details>;
}
