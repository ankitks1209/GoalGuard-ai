import { useEffect, useRef, useState } from 'react';
import type { OwnerApi } from './api';
import type { Preview } from './types';
import { sampleDraftText } from './sampleDraft';

interface DraftReply { status: string; preview?: Preview; questions?: string[] }
export function AiDraft({ api, version, disabled, onReady, onBusy }: {
  api: OwnerApi; version: string; disabled: boolean; onReady: (value: Preview) => void; onBusy: (value: boolean) => void;
}) {
  const [sample] = useState(sampleDraftText);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [questions, setQuestions] = useState<string[]>([]);
  const [ready, setReady] = useState(false);
  const generation = useRef(0);
  const running = useRef(false);
  useEffect(() => {
    generation.current++; setConsent(false); setError(''); setQuestions([]); setReady(false);
    return () => { generation.current++; };
  }, [version]);
  async function draft() {
    if (running.current || disabled || !version || !consent) return;
    running.current = true; setBusy(true); onBusy(true); setError(''); setQuestions([]); setReady(false);
    const current = generation.current;
    try {
      const result = await api.request<DraftReply>('/v1/plan/draft', {
        request: sample, timezone: 'UTC', currency: 'USD', allow_model_processing: true,
      });
      if (current !== generation.current) return;
      if (result.status === 'draft_ready') {
        const preview = result.preview;
        if (!preview?.spec || !preview.summary || preview.mode !== 'activate' || !preview.preview_hash ||
          (preview.activation_blocked_by !== null && typeof preview.activation_blocked_by !== 'string') || !Array.isArray(preview.releases_purchase_ids)) {
          throw new Error('The draft response was incomplete. Use manual entry or request a fresh sample draft.');
        }
        onReady(preview); setReady(true);
      } else if (['needs_clarification', 'needs_manual_entry'].includes(result.status)) {
        setQuestions(Array.isArray(result.questions) && result.questions.every(question => typeof question === 'string')
          ? result.questions : ['The sample needs clarification. Continue with manual entry below.']);
      } else throw new Error('The draft response was not recognized. Continue with manual entry below.');
    } catch (caught) {
      if (current === generation.current) setError((caught as Error).message);
    } finally { running.current = false; setBusy(false); onBusy(false); }
  }
  return <details className="plan-section ai-draft">
    <summary><span>Try AI drafting with sample data</span><small className="section-hint">Optional. Review a draft before confirming any plan.</small></summary>
    <div className="section-content">
      <p>This demo sends only the fixed sample below to Google Gemini. Your form entries, existing financial records and credentials are not included. Personal financial text is not accepted.</p>
      <p className="muted">Google may use free-tier inputs to improve its products. <a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noreferrer">Review Gemini data-use terms</a>.</p>
      <label htmlFor="ai-sample">Sample text sent to Gemini</label>
      <textarea id="ai-sample" rows={5} readOnly value={sample} />
      <label className="checkbox-label"><input type="checkbox" checked={consent} disabled={busy || disabled || !version} onChange={event => setConsent(event.target.checked)} />I agree to send this sample to Google Gemini for drafting.</label>
      <button type="button" disabled={busy || disabled || !version || !consent} onClick={() => void draft()}>{busy ? 'Drafting sample…' : 'Create sample AI draft'}</button>
      {busy && <p role="status">Creating a sample draft. No plan will be activated.</p>}
      {error && <p className="notice" role="alert">{error} Manual entry below remains available. No request will retry automatically.</p>}
      {!!questions.length && <div className="notice" role="status"><p>The draft needs your review. Use manual entry below to resolve these points.</p><ul>{questions.map((question, index) => <li key={index}>{question}</li>)}</ul></div>}
      {ready && <p className="notice" role="status">Sample draft ready. Review every amount, date and bill below. Nothing is active until you confirm the exact preview.</p>}
    </div>
  </details>;
}
