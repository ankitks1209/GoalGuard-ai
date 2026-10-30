import type { AuditEvent } from './types';
import { money } from './types';
export function Timeline({ events, reading, onRefresh }: { events: AuditEvent[] | null; reading: boolean; onRefresh: () => Promise<void> }) {
  return <section className="timeline-view" aria-label="Your timeline">
    <header className="page-heading">
      <h1>Your timeline</h1>
      <p className="muted">Recorded plan and purchase events. Refreshing this view never initiates payment.</p>
      <div className="timeline-toolbar"><span>Latest recorded events first</span><div className="actions"><button onClick={() => void onRefresh()}>Refresh workspace</button><small>Reads current status. No payment retries.</small></div></div>
    </header>
    {reading && <p role="status">{events ? 'Refreshing your timeline…' : 'Loading your timeline…'}</p>}
    {!events && !reading && <p className="notice">Timeline is unavailable. Refresh workspace to read current status.</p>}
    {events && (!events.length ? <div className="empty-state"><h2>A fresh start</h2><p>Your confirmed plans, reservations and payment updates will appear here.</p></div> :
      <ol className="timeline" aria-label="Recorded events">{events.map(event => <li key={event.id}>
        <time dateTime={new Date(event.at * 1000).toISOString()}>{new Date(event.at * 1000).toLocaleString()}</time>
        <div><h2>{event.event.replaceAll('_', ' ')}</h2><p>{event.purchase_id ?? 'Financial plan'}</p>
          {event.event === 'cash_recorded' && <>
            <p>{typeof event.details.kind === 'string' && Number.isSafeInteger(event.details.amount_cents)
              ? `${event.details.kind.replaceAll('_', ' ')}: ${money(event.details.amount_cents as number)}.` : 'Financial record details are unavailable.'}</p>
            {typeof event.details.reference_id === 'string' && <p>Linked record: {event.details.reference_id}</p>}
            {typeof event.details.event_id === 'string' && <p>Record ID: {event.details.event_id}</p>}
          </>}
        </div>
      </li>)}</ol>)}
  </section>;
}
