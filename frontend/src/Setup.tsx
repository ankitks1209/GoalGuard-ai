import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, OwnerApi } from './api';
import type { Overview, Session } from './types';
import { money } from './types';
import { PlanEditor } from './PlanEditor';
import { Purchases } from './Purchases';
import { Timeline } from './Timeline';

const navigation = [
  { name: 'Plan', label: 'budget', description: 'plan and protection',
    path: 'M8 10H48V54H8Z M14 18H42V32H14Z M15 41H20 M26 41H31 M37 41H42 M15 47H20 M26 47H31 M37 47H42' },
  { name: 'Purchases', label: 'purchases', description: 'requests and consent',
    path: 'M8 19H48V55H8Z M8 19L18 9H38L48 19 M8 25H48 M28 9V55' },
  { name: 'Timeline', label: 'timeline', description: 'events and decisions',
    path: 'M8 9H48V55H8Z M14 17H42 M14 24H42 M14 31H42 M14 38H34 M14 45H29' },
];

export function Setup() {
  const [session, setSession] = useState<Session | null>(null);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [reading, setReading] = useState(false);
  const [screen, setScreen] = useState('Plan');
  const epoch = useRef(0);
  const apiRef = useRef<OwnerApi | null>(null);
  if (!apiRef.current) apiRef.current = new OwnerApi(() => lock('Session expired. Unlock again; your unsaved input is retained. No changes will be retried automatically.'));
  const api = apiRef.current;

  function lock(message: string) {
    epoch.current++;
    if (apiRef.current) apiRef.current.csrf = '';
    setSession(null); setOverview(null); setReading(false); setNotice(message);
  }
  async function refresh() {
    const current = epoch.current;
    setReading(true);
    try {
      const data = await api.request<Overview>('/v1/owner/overview');
      if (!data || !Array.isArray(data.purchases) || !Array.isArray(data.events) || data.plan === undefined) {
        throw new Error('The workspace response was incomplete. Check the local server and refresh status.');
      }
      if (current === epoch.current) { setOverview(data); setNotice(''); }
    } catch (error) {
      if (current === epoch.current) setNotice((error as Error).message);
    } finally {
      if (current === epoch.current) setReading(false);
    }
  }
  function accept(value: Session) {
    if (!value || typeof value.csrf_token !== 'string' || !value.csrf_token || !Number.isFinite(value.expires_in_seconds) || value.expires_in_seconds <= 0 || value.expires_in_seconds > 1800) {
      throw new Error('Invalid session response. Unlock again after checking the server.');
    }
    epoch.current++;
    api.csrf = value.csrf_token;
    setSession(value); setNotice('');
    void refresh();
  }
  useEffect(() => {
    let active = true;
    api.request<Session>('/v1/owner/session').then(value => { if (active) accept(value); })
      .catch(error => { if (active) setNotice(error instanceof ApiError && error.status === 401 ? '' : (error as Error).message); })
      .finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, [api]);
  useEffect(() => {
    if (!session) return;
    const timer = window.setTimeout(() => lock('Session expired. Unlock again; your unsaved input is retained. No changes will be retried automatically.'), session.expires_in_seconds * 1000);
    return () => window.clearTimeout(timer);
  }, [session]);

  async function unlock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem('owner-key') as HTMLInputElement;
    const key = input.value;
    input.value = '';
    setBusy(true); setNotice('');
    try { accept(await api.request<Session>('/v1/owner/session', {}, key)); }
    catch (error) { setNotice(error instanceof ApiError && error.status === 401 ? 'Owner key was not accepted. Try your owner key again.' : (error as Error).message); }
    finally { setBusy(false); }
  }
  async function logout() {
    setBusy(true);
    try { await api.request('/v1/owner/logout', {}); lock('Workspace locked.'); }
    catch (error) { setNotice((error as Error).message); }
    finally { setBusy(false); }
  }

  const plan = session ? overview?.plan : null;
  return (
    <div className="workspace">
      <a className="skip" href="#main">Skip to content</a>
      <aside className="sidebar">
        <a className="brand" href="#main" aria-label="GoalGuard">goal<span>guard</span></a>
        <nav aria-label="Workspace">{navigation.map(({ name, label, description, path }) =>
          <button key={name} aria-label={name === 'Plan' ? 'Budget and plan' : name}
            aria-current={screen === name ? 'page' : undefined} onClick={() => setScreen(name)}>
            <svg className="nav-icon" viewBox="0 0 56 64" aria-hidden="true"><path d={path} /></svg>
            <span><span className="nav-name">{label}</span><span className="nav-description">{description}</span></span>
          </button>)}</nav>
      </aside>
      <div className="workspace-body">
        <header className="topbar"><span>Owner workspace / <strong>{screen === 'Plan' ? 'Budget' : screen}</strong></span><div><span className="badge">PayPal sandbox</span>{session && <button className="text-button" disabled={busy} onClick={() => void logout()}>Lock workspace</button>}</div></header>
        <main id="main" tabIndex={-1}>
          {notice && <p role="alert" className="notice">{notice}</p>}
          <div className="budget-workspace" hidden={screen !== 'Plan' && !!session}>
            <section className="budget-overview" aria-label="Plan overview">
              <h1>Your budget.<br />In your hands.</h1>
              <p className="balance-label">Safely spendable</p>
              <div className="amount">{plan ? money(plan.available_cents) : '—'}</div>
              <p className="currency">USD. After protections and commitments.</p>
              <dl className="budget-facts">{[
                ['Cash balance', plan?.cash_base_cents], ['Protected', plan?.protected_cents],
                ['Purchase commitments', plan?.encumbered_cents], ['Captured spending', plan?.spent_cents],
              ].map(([label, value]) => <div className="fact-row" key={String(label)}><dt>{label}</dt><dd>{typeof value === 'number' ? money(value) : '—'}</dd></div>)}</dl>
            </section>
            <section className="request-summary" aria-labelledby="requests-title" hidden={!session}>
              <h2 id="requests-title">Purchase requests</h2>
              <p className="muted">Review the exact cart before giving consent.</p>
              {!overview ? <p>{reading ? 'Reading current requests…' : 'Requests are unavailable. Refresh workspace to read current status.'}</p>
                : !overview.purchases.length ? <div className="empty-state"><h3>No requests to review</h3><p>Scoped agents can propose synthetic catalog purchases after you confirm a plan.</p></div>
                : <ul className="request-list">{overview.purchases.map(purchase => <li key={purchase.id}>
                  <div className="request-title"><h3>{purchase.agent}</h3><strong>{money(purchase.amount_cents)}</strong></div>
                  <p className="muted">{purchase.cart.merchant}. {purchase.state.replaceAll('_', ' ')}.</p>
                  <button className="primary" aria-label={`Review cart from ${purchase.agent}`} onClick={() => setScreen('Purchases')}>Review cart</button>
                </li>)}</ul>}
            </section>
          </div>
          {checking ? <p role="status">Checking your local session…</p> : !session && <section className="unlock-panel" aria-labelledby="unlock-title"><div><h2 id="unlock-title">Unlock your workspace</h2><p>Use your local owner key to review your plan and purchase requests.</p><p className="muted">Sessions last 30 minutes. Financial commitments stay protected when you lock.</p></div><form onSubmit={event => void unlock(event)}><label htmlFor="owner-key">Owner key</label><input id="owner-key" name="owner-key" type="password" autoComplete="off" required disabled={busy} /><button className="primary" disabled={busy}>{busy ? 'Unlocking…' : 'Unlock workspace'}</button><small>Your key is used only to unlock this local session.</small></form></section>}
          <section hidden={!session}>
            {reading && screen === 'Plan' && <p role="status">Loading your workspace…</p>}
            <div className="actions" hidden={screen !== 'Plan'}><button onClick={() => void refresh()}>Refresh workspace</button><small>Reads current status. No payment retries.</small></div>
            <div hidden={screen !== 'Plan' || !overview}><PlanEditor api={api} overview={overview} version={session?.csrf_token ?? ''} onRefresh={refresh} /></div>
            <div hidden={screen !== 'Purchases'}><Purchases api={api} overview={overview} reading={reading} version={session?.csrf_token ?? ''} onRefresh={refresh} /></div>
            <div hidden={screen !== 'Timeline'}><Timeline events={overview?.events ?? null} reading={reading} onRefresh={refresh} /></div>
          </section>
          <footer><span>Your approval. Every exact cart.</span><span>Synthetic catalog. Manual fulfilment. PayPal sandbox.</span></footer>
        </main>
      </div>
    </div>
  );
}
