import { afterEach, expect, it, vi } from 'vitest';
import { OwnerApi } from './api';
afterEach(() => vi.unstubAllGlobals());
it('does not treat a late mutation response as a result for a new session', async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const api = new OwnerApi(vi.fn()); api.csrf = 'first-session';
  const pending = api.request('/v1/plan/confirm', { preview_hash: 'old' });
  api.csrf = 'new-session';
  finish(new Response('{}'));
  await expect(pending).rejects.toThrow(/Session changed/);
});
it('reports unreadable responses without echoing server content', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>unexpected</html>')));
  await expect(new OwnerApi(vi.fn()).request('/v1/owner/session')).rejects.toThrow(/unreadable response/);
});
it('does not let an old unauthorized response lock a newly unlocked session', async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const expired = vi.fn();
  const api = new OwnerApi(expired); api.csrf = 'old-session';
  const pending = api.request('/v1/owner/overview');
  api.csrf = 'new-session';
  finish(new Response('{}', { status: 401 }));
  await expect(pending).rejects.toThrow();
  expect(expired).not.toHaveBeenCalled();
  expect(api.csrf).toBe('new-session');
});
