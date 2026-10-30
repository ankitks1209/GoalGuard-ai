import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Setup } from './Setup';

const empty = { plan: null, draft: null, purchases: [], events: [] };
const session = { csrf_token: 'fixture-csrf', expires_in_seconds: 1800 };
const fetcher = vi.fn();
function reply(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status }); }

beforeEach(() => {
  vi.stubGlobal('fetch', fetcher);
  fetcher.mockReset().mockImplementation(async (path: string) =>
    path === '/v1/owner/session' ? reply({}, 401) : reply(empty));
});
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
async function unlock() {
  await screen.findByLabelText('Owner key');
  fireEvent.change(screen.getByLabelText('Owner key'), { target: { value: 'fixture-owner-key' } });
  fireEvent.click(screen.getByRole('button', { name: 'Unlock workspace' }));
  await screen.findByRole('button', { name: 'Lock workspace' });
}

describe('owner workspace sessions', () => {
  it('checks the session, then unlocks with an ephemeral key and never persists credentials', async () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem');
    render(<Setup />);
    await screen.findByLabelText('Owner key');
    fetcher.mockImplementation(async (path: string, init?: RequestInit) =>
      path === '/v1/owner/session' && init?.method === 'POST' ? reply(session) : reply(empty));
    await unlock();
    expect(fetcher).toHaveBeenCalledWith('/v1/owner/session', expect.objectContaining({
      method: 'POST', credentials: 'same-origin', body: '{}',
      headers: expect.objectContaining({ Authorization: 'Bearer fixture-owner-key' }),
    }));
    expect(screen.queryByDisplayValue('fixture-owner-key')).toBeNull();
    expect(storage).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: /Your budget/ })).toBeTruthy();
    expect(screen.getByText('No plan confirmed yet')).toBeTruthy();
    storage.mockRestore();
  });

  it('shows connection and unlock failures without exposing the key', async () => {
    fetcher.mockRejectedValue(new Error('fixture transport failure'));
    render(<Setup />);
    await screen.findByText(/Could not connect/);
    fetcher.mockResolvedValue(reply({}, 401));
    fireEvent.change(screen.getByLabelText('Owner key'), { target: { value: 'fixture-bad-key' } });
    fireEvent.click(screen.getByRole('button', { name: 'Unlock workspace' }));
    await screen.findByText(/Owner key was not accepted/);
    expect(screen.queryByDisplayValue('fixture-bad-key')).toBeNull();
  });

  it('ends workspace loading after a failed read and waits for a deliberate refresh', async () => {
    fetcher.mockImplementation(async (path: string) => path === '/v1/owner/session'
      ? reply(session) : reply({ reason: 'unavailable', message: 'Read unavailable. Refresh status.' }, 503));
    render(<Setup />);
    await screen.findByRole('alert');
    expect(screen.queryByText('Loading your workspace…')).toBeNull();
    expect(fetcher.mock.calls.filter(([path]) => path === '/v1/owner/overview')).toHaveLength(1);
    fetcher.mockImplementation(async () => reply(empty));
    fireEvent.click(screen.getByRole('button', { name: 'Refresh workspace' }));
    await screen.findByRole('heading', { name: 'No plan confirmed yet' });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('distinguishes unread purchases from an empty result and recovers only on deliberate refresh', async () => {
    let finishRead!: (response: Response) => void;
    const read = new Promise<Response>(resolve => { finishRead = resolve; });
    fetcher.mockImplementation(async (path: string) => path === '/v1/owner/session' ? reply(session) : read);
    render(<Setup />);
    fireEvent.click(await screen.findByRole('button', { name: 'Purchases' }));
    expect(screen.queryByRole('heading', { name: 'No purchase requests yet' })).toBeNull();
    expect(screen.getByRole('status').textContent).toBe('Loading purchase requests…');
    expect(screen.queryByText('0 requests')).toBeNull();
    await act(async () => { finishRead(reply({ reason: 'unavailable', message: 'Purchase read unavailable.' }, 503)); });
    await screen.findByRole('alert');
    expect(screen.queryByRole('status')).toBeNull();
    expect(screen.queryByRole('heading', { name: 'No purchase requests yet' })).toBeNull();
    expect(screen.getByText('Purchase requests are unavailable. Refresh workspace to read current status.')).toBeTruthy();
    expect(fetcher.mock.calls.filter(([path]) => path === '/v1/owner/overview')).toHaveLength(1);
    fetcher.mockImplementation(async () => reply(empty));
    fireEvent.click(screen.getByRole('button', { name: 'Refresh workspace' }));
    await screen.findByRole('heading', { name: 'No purchase requests yet' });
    expect(screen.getByText('0 requests')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(fetcher.mock.calls.filter(([path]) => path === '/v1/owner/overview')).toHaveLength(2);
    expect(fetcher.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false);
  });

  it('distinguishes an unread timeline from an empty history and recovers only on deliberate refresh', async () => {
    let finishRead!: (response: Response) => void;
    const read = new Promise<Response>(resolve => { finishRead = resolve; });
    fetcher.mockImplementation(async (path: string) => path === '/v1/owner/session' ? reply(session) : read);
    render(<Setup />);
    fireEvent.click(await screen.findByRole('button', { name: 'Timeline' }));
    expect(screen.queryByRole('heading', { name: 'A fresh start' })).toBeNull();
    expect(screen.getByRole('status').textContent).toBe('Loading your timeline…');
    await act(async () => { finishRead(reply({ reason: 'unavailable', message: 'Timeline read unavailable.' }, 503)); });
    await screen.findByRole('alert');
    expect(screen.queryByRole('status')).toBeNull();
    expect(screen.queryByRole('heading', { name: 'A fresh start' })).toBeNull();
    expect(screen.getByText('Timeline is unavailable. Refresh workspace to read current status.')).toBeTruthy();
    expect(fetcher.mock.calls.filter(([path]) => path === '/v1/owner/overview')).toHaveLength(1);
    fetcher.mockImplementation(async () => reply(empty));
    fireEvent.click(screen.getByRole('button', { name: 'Refresh workspace' }));
    await screen.findByRole('heading', { name: 'A fresh start' });
    expect(screen.queryByRole('alert')).toBeNull();
    expect(fetcher.mock.calls.filter(([path]) => path === '/v1/owner/overview')).toHaveLength(2);
    expect(fetcher.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false);
  });

  it('restores an existing session, locks on expiry and retains unsaved non-secret input', async () => {
    fetcher.mockImplementation(async (path: string) => path === '/v1/owner/session' ? reply({ ...session, expires_in_seconds: 0.08 }) : reply(empty));
    render(<Setup />);
    await screen.findByRole('button', { name: 'Lock workspace' });
    fireEvent.change(screen.getByLabelText('Plan name'), { target: { value: 'Our household' } });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 100)); });
    await screen.findByText(/Session expired/);
    fetcher.mockImplementation(async (path: string) => path === '/v1/owner/session' ? reply(session) : reply(empty));
    const before = fetcher.mock.calls.filter(([, init]) => init?.method === 'POST').length;
    await unlock();
    expect(screen.getByLabelText('Plan name')).toHaveProperty('value', 'Our household');
    expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'POST').length).toBe(before + 1);
  });

  it('logs out with session CSRF and shows the locked state', async () => {
    const privateView = { ...empty, purchases: [{ id: 'fixture-private-purchase', agent: 'fixture-agent', state: 'approved',
      amount_cents: 10000, cart_hash: 'fixture-hash', expires_at: Date.now() / 1000 + 900, permit: 'fixture-consent', operation_id: null, order_id: null,
      cart: { merchant: 'fixture-merchant', currency: 'USD', items: [{ sku: 'private-cart-fixture', quantity: 1, unit_cents: 10000 }], shipping_cents: 0, tax_cents: 0 } }] };
    fetcher.mockImplementation(async (path: string) => path === '/v1/owner/session' ? reply(session) : reply(privateView));
    render(<Setup />);
    await screen.findByText('private-cart-fixture');
    fireEvent.click(await screen.findByRole('button', { name: 'Lock workspace' }));
    await screen.findByLabelText('Owner key');
    expect(screen.queryByText('private-cart-fixture')).toBeNull();
    await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/v1/owner/logout', expect.objectContaining({
      method: 'POST', headers: expect.objectContaining({ 'X-CSRF-Token': 'fixture-csrf' }),
    })));
  });
});
