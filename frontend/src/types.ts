export interface PlanSpec {
  title: string; timezone: string; currency: 'USD'; opening_cash_cents: number; buffer_cents: number;
  next_income: { id: string; due_date: string; amount_cents: number } | null;
  bills: { id: string; name: string; amount_cents: number; due_date: string }[];
  goal: { id: string; title: string; target_cents: number; current_saved_cents: number;
    target_date: string; contribution_cents: number } | null;
}
export interface Summary {
  title?: string; spec: PlanSpec; status: string; can_propose: boolean;
  cash_base_cents: number; protected_cents: number; protected_bills_cents: number;
  buffer_cents: number; remaining_goal_contribution_cents: number;
  encumbered_cents: number; spent_cents: number; available_cents: number; projected_surplus_cents: number;
  goal?: { suggested_contribution_cents: number; schedule_off_track: boolean } | null;
}
export interface Preview { spec: PlanSpec; mode: string; summary: Omit<Summary, 'spec'>; preview_hash: string; activation_blocked_by: string | null; releases_purchase_ids: string[] }
export interface Purchase {
  id: string; agent: string; state: string; cart_hash: string; amount_cents: number; expires_at: number;
  permit: string | null; operation_id: string | null; order_id: string | null;
  cart: { merchant: string; currency: string; items: { sku: string; quantity: number; unit_cents: number }[];
    shipping_cents: number; tax_cents: number };
}
export interface AuditEvent { id: string; at: number; event: string; purchase_id: string | null; details: Record<string, unknown> }
export interface Overview { plan: Summary | null; draft: { mode: string; spec: PlanSpec } | null; purchases: Purchase[]; events: AuditEvent[] }
export interface Session { csrf_token: string; expires_in_seconds: number }
export const money = (cents: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);
