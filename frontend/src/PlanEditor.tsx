import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { OwnerApi } from './api';
import type { Overview, PlanSpec, Preview } from './types';
import { money } from './types';
import { parseMoney } from './moneyInput';
import { AiDraft } from './AiDraft';
import { CashEvents } from './CashEvents';

type Bill = { id: string; name: string; amount: string; due: string };
interface Form {
  title: string; timezone: string; cash: string; buffer: string; incomeId: string; payday: string; income: string;
  unknownIncome: boolean; bills: Bill[]; goalEnabled: boolean; goalId: string; goalTitle: string;
  target: string; saved: string; deadline: string; contribution: string;
}
const blank: Form = { title: '', timezone: '', cash: '', buffer: '', incomeId: 'next-income', payday: '', income: '',
  unknownIncome: false, bills: [], goalEnabled: false, goalId: 'savings-goal', goalTitle: '', target: '', saved: '', deadline: '', contribution: '' };
const dollars = (value: number) => (value / 100).toFixed(2);
function fromSpec(spec: PlanSpec): Form {
  return { title: spec.title, timezone: spec.timezone, cash: dollars(spec.opening_cash_cents), buffer: dollars(spec.buffer_cents),
    incomeId: spec.next_income?.id ?? 'next-income', payday: spec.next_income?.due_date ?? '', income: spec.next_income ? dollars(spec.next_income.amount_cents) : '', unknownIncome: !spec.next_income,
    bills: spec.bills.map(bill => ({ id: bill.id, name: bill.name, amount: dollars(bill.amount_cents), due: bill.due_date })),
    goalEnabled: !!spec.goal, goalId: spec.goal?.id ?? 'savings-goal', goalTitle: spec.goal?.title ?? '', target: spec.goal ? dollars(spec.goal.target_cents) : '',
    saved: spec.goal ? dollars(spec.goal.current_saved_cents) : '', deadline: spec.goal?.target_date ?? '', contribution: spec.goal ? dollars(spec.goal.contribution_cents) : '' };
}

export function PlanEditor({ api, overview, version, onRefresh }: { api: OwnerApi; overview: Overview | null; version: string; onRefresh: () => Promise<void> }) {
  const [form, setForm] = useState<Form>(blank);
  const [mode, setMode] = useState('activate');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [otherBusy, setOtherBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const dirty = useRef(false);
  const running = useRef(false);
  const generation = useRef(0);
  useEffect(() => {
    const source = overview?.draft?.spec ?? overview?.plan?.spec;
    if (!dirty.current && source) { setForm(fromSpec(source)); setMode(overview?.draft?.mode ?? 'revise'); }
  }, [overview]);
  useEffect(() => { generation.current++; setPreview(null); setError(''); }, [version]);
  function update<K extends keyof Form>(key: K, value: Form[K]) {
    dirty.current = true; setForm(current => ({ ...current, [key]: value })); setPreview(null); setMessage('');
  }
  function spec(): PlanSpec {
    return { title: form.title, timezone: form.timezone, currency: 'USD', opening_cash_cents: parseMoney(form.cash), buffer_cents: parseMoney(form.buffer),
      next_income: form.unknownIncome ? null : { id: form.incomeId, due_date: form.payday, amount_cents: parseMoney(form.income) },
      bills: form.bills.map(bill => ({ id: bill.id, name: bill.name, amount_cents: parseMoney(bill.amount), due_date: bill.due })),
      goal: form.goalEnabled ? { id: form.goalId, title: form.goalTitle, target_cents: parseMoney(form.target), current_saved_cents: parseMoney(form.saved), target_date: form.deadline, contribution_cents: parseMoney(form.contribution) } : null };
  }
  async function run(confirm: boolean) {
    if (running.current || otherBusy || !version) return;
    running.current = true; setBusy(true); setError(''); setMessage('');
    const current = generation.current;
    try {
      if (confirm && preview) {
        await api.request('/v1/plan/confirm', { plan: preview.spec, mode: preview.mode, preview_hash: preview.preview_hash });
        if (current === generation.current) { dirty.current = false; setMode('revise'); setPreview(null); setMessage('Plan confirmed. Your protections are active.'); }
        await onRefresh();
      } else {
        const result = await api.request<Preview>('/v1/plan/preview', { plan: spec(), mode });
        if (current === generation.current) setPreview(result);
      }
    } catch (caught) {
      if (current === generation.current) { setPreview(null); setError((caught as Error).message); }
    } finally { running.current = false; setBusy(false); }
  }
  const field = (key: keyof Form, label: string, type = 'text', helper?: string) => <div className="field" key={key}>
    <label htmlFor={`plan-${key}`}>{label}</label><input id={`plan-${key}`} value={String(form[key])} type={type} required maxLength={120}
      inputMode={['cash', 'buffer', 'income', 'target', 'saved', 'contribution'].includes(key) ? 'decimal' : undefined}
      onChange={event => update(key, event.target.value)} /><small>{helper}</small></div>;
  const submit = (event: FormEvent) => { event.preventDefault(); void run(false); };
  return <>
    <section className="panel">
      <div className="section-top"><div><h2>{overview?.plan ? 'Your financial plan' : 'No plan confirmed yet'}</h2><p>Start with cash, a buffer and your next income. Open the other sections when needed.</p></div><span className="status-label">{overview?.plan?.status.replaceAll('_', ' ') ?? 'Setup needed'}</span></div>
      {error && <p className="notice" role="alert">{error}</p>}{message && <p className="notice" role="status">{message}</p>}
      {!overview?.plan && <AiDraft api={api} version={version} disabled={busy} onBusy={value => { setOtherBusy(value); if (value) setPreview(null); }} onReady={value => {
        dirty.current = true; setForm(fromSpec(value.spec)); setMode('activate'); setPreview(value); setError(''); setMessage('');
      }} />}
      <form onSubmit={submit} onInvalid={event => {
        if (event.target instanceof HTMLElement) event.target.closest('details')?.setAttribute('open', '');
      }}>
        <fieldset disabled={busy || otherBusy}>
          <div className="form-grid">
            {field('cash', 'Current cash (USD)', 'text', 'Cash available now, excluding separately held savings.')}
            {field('buffer', 'Cash buffer (USD)', 'text', 'The cushion your agents cannot spend.')}
          </div>
          <div className="line" />
          <h3>Next income</h3><p className="muted">Expected income is a forecast. It never authorizes spending today.</p>
          <label className="checkbox-label"><input type="checkbox" checked={form.unknownIncome} onChange={event => update('unknownIncome', event.target.checked)} />Next payday is not known yet</label>
          {!form.unknownIncome && <div className="form-grid">{field('payday', 'Next payday', 'date')}{field('income', 'Expected income (USD)')}</div>}
          <details className="plan-section">
          <summary><span>Bills to protect</span><small className="section-hint">{form.bills.length ? `${form.bills.length} bill${form.bills.length === 1 ? '' : 's'} entered. Included in the preview.` : 'Add overdue and upcoming bills.'}</small></summary>
          <div className="section-content">
          <div className="section-top"><p>Include every bill that needs protection. Closing this section keeps your entries.</p><button type="button" onClick={() => update('bills', [...form.bills, { id: crypto.randomUUID(), name: '', amount: '', due: '' }])}>+ Add bill</button></div>
          {!form.bills.length && <p className="muted">No bills entered. Add each bill you want your plan to protect.</p>}
          {form.bills.map((bill, index) => <div className="bill-row" key={bill.id}>{([
            ['name', `Bill ${index + 1} name`, 'text'], ['amount', `Bill ${index + 1} amount (USD)`, 'text'], ['due', `Bill ${index + 1} due date`, 'date'],
          ] as const).map(([key, label, type]) => <div key={key}><label htmlFor={`${bill.id}-${key}`}>{label}</label><input id={`${bill.id}-${key}`} type={type} value={bill[key]} required onChange={event => update('bills', form.bills.map(item => item.id === bill.id ? { ...item, [key]: event.target.value } : item))} /></div>)}<button type="button" aria-label={`Remove bill ${index + 1}`} onClick={() => update('bills', form.bills.filter(item => item.id !== bill.id))}>Remove</button></div>)}
          </div>
          </details>
          <details className="plan-section">
          <summary><span>Savings</span><small className="section-hint">{form.goalEnabled ? 'Goal included in the preview.' : 'Add a goal if you have one.'}</small></summary>
          <div className="section-content">
          <label className="checkbox-label"><input type="checkbox" checked={form.goalEnabled} onChange={event => update('goalEnabled', event.target.checked)} />Include a savings goal</label>
          {form.goalEnabled && <div className="form-grid">{field('goalTitle', 'Savings goal')}{field('target', 'Savings target (USD)')}{field('saved', 'Already saved (USD)')}{field('deadline', 'Goal deadline', 'date')}{field('contribution', 'Monthly contribution (USD)', 'text', 'The preview shows the server-calculated suggestion and any off-track override.')}</div>}
          </div>
          </details>
          <details className="plan-section">
          <summary><span>Plan details</span><small className="section-hint">{form.title && form.timezone ? `${form.title}. ${form.timezone}.` : 'Plan name and timezone required before preview.'}</small></summary>
          <div className="section-content">
          <div className="form-grid">{field('title', 'Plan name')}{field('timezone', 'Timezone', 'text', 'Your confirmed IANA timezone, e.g. Asia/Kolkata.')}</div>
          {overview?.plan && <div className="field"><label htmlFor="plan-mode">Plan change</label><select id="plan-mode" value={mode} onChange={event => { setMode(event.target.value); setPreview(null); }}><option value="revise">Revise current plan</option><option value="rollover">Confirm next period</option></select><small>Use “Record a financial update” below for actual cash changes. Opening cash cannot be rewritten on a revision.</small></div>}
          </div>
          </details>
          <div className="actions"><button className="primary" disabled={!version}>{busy ? 'Checking…' : 'Preview protections'}</button><small>USD only · No money moves</small></div>
        </fieldset>
      </form>
    </section>
    {preview && <section className="panel review" aria-labelledby="review-title"><h2 id="review-title">Review your protections</h2><p>{preview.spec.title}. Timezone: {preview.spec.timezone}. {preview.spec.bills.length} bill(s) included. {preview.spec.goal ? 'Savings goal included.' : 'No savings goal.'}</p><dl>
      <dt>Cash available now</dt><dd>{money(preview.summary.cash_base_cents)}</dd><dt>Protected bills</dt><dd>{money(preview.summary.protected_bills_cents)}</dd><dt>Cash buffer</dt><dd>{money(preview.summary.buffer_cents)}</dd><dt>Savings contribution</dt><dd>{money(preview.summary.remaining_goal_contribution_cents)}</dd><dt>Available to spend</dt><dd>{money(preview.summary.available_cents)}</dd><dt>Forecast with expected income</dt><dd>{money(preview.summary.projected_surplus_cents)}</dd>
    </dl><p>Status: <strong>{preview.summary.status.replaceAll('_', ' ')}</strong></p>
      <h3>Dates and obligations</h3>
      <p>{preview.spec.next_income ? `Expected income: ${money(preview.spec.next_income.amount_cents)} on ${preview.spec.next_income.due_date}.` : 'Next income is not known.'} Expected income is a forecast only.</p>
      {preview.spec.bills.length ? <ul>{preview.spec.bills.map(bill => <li key={bill.id}>{bill.name}: {money(bill.amount_cents)}, due {bill.due_date}.</li>)}</ul> : <p>No bills included. Confirm that none are missing.</p>}
      {preview.spec.goal && <p>{preview.spec.goal.title}: target {money(preview.spec.goal.target_cents)} by {preview.spec.goal.target_date}; {money(preview.spec.goal.current_saved_cents)} already saved separately.</p>}
      {preview.spec.goal && preview.summary.goal && <p>Suggested monthly contribution: {money(preview.summary.goal.suggested_contribution_cents)}. Your confirmed amount: {money(preview.spec.goal.contribution_cents)}. {preview.summary.goal.schedule_off_track && 'Your chosen contribution is off track for this goal.'}</p>}
      {!!preview.releases_purchase_ids.length && <div className="notice"><p>This change releases {preview.releases_purchase_ids.length} pre-payment reservation(s). Review affected purchases before confirming.</p><ul>{preview.releases_purchase_ids.map(id => <li className="purchase-id" key={id}>{id}</li>)}</ul></div>}
      {!!preview.activation_blocked_by && <p className="notice">Cannot confirm yet: {preview.activation_blocked_by.replaceAll('_', ' ')}. Update your plan or resolve the pending payment.</p>}
      <p className="muted">Confirmation binds these exact terms to the current ledger. Changed obligations require a fresh preview.</p><button className="primary" disabled={busy || otherBusy || !version || !!preview.activation_blocked_by} onClick={() => void run(true)}>Confirm this plan</button>
    </section>}
    <CashEvents api={api} overview={overview} version={version} disabled={busy} onBusy={setOtherBusy}
      onInvalidate={() => setPreview(null)} onRefresh={onRefresh} />
  </>;
}
