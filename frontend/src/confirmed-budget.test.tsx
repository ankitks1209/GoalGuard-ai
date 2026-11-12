import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { Setup } from './Setup';
import type { Overview, PlanSpec } from './types';

const spec: PlanSpec = { title: 'Our budget', timezone: 'UTC', currency: 'USD', opening_cash_cents: 60000,
  buffer_cents: 5000, next_income: { id: 'pay', due_date: '2026-11-05', amount_cents: 40000 },
  bills: [{ id: 'utilities', name: 'Utilities', amount_cents: 10000, due_date: '2026-11-02' }], goal: null };
const plan = { spec, status: 'ready', can_propose: true, cash_base_cents: 60000, protected_cents: 15000,
  protected_bills_cents: 10000, buffer_cents: 5000, remaining_goal_contribution_cents: 0,
  encumbered_cents: 0, spent_cents: 0, available_cents: 45000, projected_surplus_cents: 85000 };
const preview = { spec, mode: 'activate', summary: plan, preview_hash: 'exact-reviewed-budget',
  activation_blocked_by: null, releases_purchase_ids: [] };
let view: Overview;
let confirmed: boolean;
const fetcher = vi.fn();
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
beforeEach(() => {
  view = { plan: null, draft: { spec, mode: 'activate' }, purchases: [], events: [] };
  confirmed = false;
  vi.stubGlobal('fetch', fetcher);
  fetcher.mockReset().mockImplementation(async (path: string) => {
    if (path === '/v1/owner/session') return reply({ csrf_token: 'fixture-session', expires_in_seconds: 1800 });
    if (path === '/v1/plan/preview') return reply(preview);
    if (path === '/v1/plan/confirm') { confirmed = true; view = { ...view, plan, draft: null }; return reply(plan); }
    return reply(view);
  });
});
afterEach(() => vi.unstubAllGlobals());
async function review() {
  render(<Setup />);
  await screen.findByDisplayValue('Our budget');
  const heading = screen.getByRole('heading', { level: 1 });
  heading.scrollIntoView = vi.fn();
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  await screen.findByRole('button', { name: 'Confirm this plan' });
  return heading;
}
const confirmations = () => fetcher.mock.calls.filter(([path]) => path === '/v1/plan/confirm');

it('shows how cash remaining after captures is allocated', async () => {
  view.plan = { ...plan, encumbered_cents: 22000, spent_cents: 20000, available_cents: 3000 };
  render(<Setup />);
  expect(await screen.findByRole('img', { name: 'Cash allocation: $150.00 protected, $220.00 committed, $30.00 spendable' })).toBeTruthy();
  expect(screen.getByText('Cash after captured spending')).toBeTruthy();
});

it.each([
  { cash: 14000, available: -1000, status: 'waiting_for_income', label: 'Budget shortfall' },
  { cash: 60000, available: 45000, status: 'income_overdue', label: 'Budget balance' },
])('shows $label without a spendable allocation while requests are paused', async ({ cash, available, status, label }) => {
  view.plan = { ...plan, cash_base_cents: cash, available_cents: available, status, can_propose: false };
  render(<Setup />);
  expect(await screen.findByRole('heading', { name: label })).toBeTruthy();
  expect(screen.getByText('New purchase requests are paused.')).toBeTruthy();
  expect(screen.queryByRole('img', { name: /Cash allocation/ })).toBeNull();
});

it('opens the refreshed budget after confirmation and lets the owner deliberately edit again', async () => {
  const normal = fetcher.getMockImplementation()!;
  let finish!: (value: Response) => void;
  fetcher.mockImplementation(async (path: string) => path === '/v1/owner/overview' && confirmed
    ? new Promise<Response>(resolve => { finish = resolve; }) : normal(path));
  const heading = await review();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm this plan' }));
  await waitFor(() => expect(finish).toBeTypeOf('function'));
  expect(screen.getByLabelText('Current cash (USD)')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Edit plan' })).toBeNull();
  await act(async () => finish(reply(view)));
  const edit = await screen.findByRole('button', { name: 'Edit plan' });
  expect(screen.queryByRole('button', { name: 'Preview protections' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Confirm this plan' })).toBeNull();
  expect(document.activeElement).toBe(heading);
  expect(heading.scrollIntoView).toHaveBeenCalledWith({ behavior: 'instant', block: 'start' });
  expect(within(screen.getByRole('region', { name: 'Plan overview' })).getByText('$450.00')).toBeTruthy();
  const budget = screen.getByRole('region', { name: 'Confirmed budget plan' });
  expect(within(budget).getByText(/Utilities/)).toBeTruthy();
  expect(within(budget).getByText('$100.00')).toBeTruthy();
  expect(within(budget).getByText(/2026-11-05/)).toBeTruthy();
  expect(screen.getByText('Record a financial update', { exact: true })).toBeTruthy();
  expect(confirmations()).toHaveLength(1);
  fireEvent.click(edit);
  expect(screen.getByRole('button', { name: 'Preview protections' })).toBeTruthy();
  expect(document.activeElement).toBe(screen.getByLabelText('Current cash (USD)'));
  expect(screen.getByLabelText('Current cash (USD)')).toHaveProperty('value', '600.00');
  expect(screen.getByLabelText('Plan change')).toHaveProperty('value', 'revise');
  expect(confirmations()).toHaveLength(1);
});

it.each(['unavailable', 'missing plan', 'expired'])('keeps the editor or lock screen when the confirmed-budget read is %s', async outcome => {
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string) => {
    if (path === '/v1/owner/overview' && confirmed) {
      if (outcome === 'missing plan') return reply({ ...view, plan: null });
      return reply({ reason: outcome, message: 'Workspace read failed. Refresh status.' }, outcome === 'expired' ? 401 : 503);
    }
    return normal(path);
  });
  const heading = await review();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm this plan' }));
  if (outcome === 'expired') await screen.findByLabelText('Owner key');
  else {
    await screen.findByRole('alert');
    expect(screen.getByRole('button', { name: 'Preview protections' })).toBeTruthy();
  }
  expect(screen.queryByRole('button', { name: 'Edit plan' })).toBeNull();
  expect(heading.scrollIntoView).not.toHaveBeenCalled();
  expect(confirmations()).toHaveLength(1);
});

it('keeps a rejected confirmation in the editor without showing a confirmed budget', async () => {
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string) => path === '/v1/plan/confirm'
    ? reply({ reason: 'stale_preview', message: 'Preview is stale. Review again.' }, 409) : normal(path));
  const heading = await review();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm this plan' }));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Preview is stale. Review again.');
  expect(screen.queryByRole('button', { name: 'Edit plan' })).toBeNull();
  expect(screen.getByRole('button', { name: 'Preview protections' })).toBeTruthy();
  expect(heading.scrollIntoView).not.toHaveBeenCalled();
  expect(confirmations()).toHaveLength(1);
});

it('ignores a late confirmed-budget read after the owner locks the workspace', async () => {
  const normal = fetcher.getMockImplementation()!;
  let finish!: (value: Response) => void;
  fetcher.mockImplementation(async (path: string) => path === '/v1/owner/overview' && confirmed
    ? new Promise<Response>(resolve => { finish = resolve; }) : normal(path));
  const heading = await review();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm this plan' }));
  await waitFor(() => expect(finish).toBeTypeOf('function'));
  fireEvent.click(screen.getByRole('button', { name: 'Lock workspace' }));
  await screen.findByLabelText('Owner key');
  await act(async () => finish(reply(view)));
  expect(screen.getByLabelText('Owner key')).toBeTruthy();
  expect(screen.queryByRole('region', { name: 'Confirmed budget plan' })).toBeNull();
  expect(heading.scrollIntoView).not.toHaveBeenCalled();
  expect(confirmations()).toHaveLength(1);
});
