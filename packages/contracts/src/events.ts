/**
 * CartGuard AI Event Schemas
 * Per MASTER_PROMPT.md Section 7: Event Schemas
 *
 * Events are append-only facts. Version schemas; tolerate additive fields; reject breaking changes.
 * No envelope or payload contains name, email, phone, raw order ID, full address, payment data, password, token, or secret.
 */

import type {
  TenantId,
  ShopId,
  SessionId,
  CartIdHash,
  DecisionId,
  PolicyVersion,
  ExperimentId,
  EventId,
  Currency,
  ConsentState,
  Cart,
  Action
} from '@cartguard/domain';

// ─────────────────────────────────────────────────────────────────────────────
// Event Envelope (Common structure for all events)
// ─────────────────────────────────────────────────────────────────────────────

export interface EventEnvelope<TPayload = unknown> {
  readonly event_id: EventId;
  readonly event_type: EventType;
  readonly schema_version: string;
  readonly occurred_at: string; // ISO 8601 UTC timestamp
  readonly received_at: string; // ISO 8601 UTC timestamp (set by server)
  readonly tenant_id: TenantId;
  readonly shop_id: ShopId;
  readonly session_id: SessionId;
  readonly source: EventSource;
  readonly trace_id: string;
  readonly payload: TPayload;
}

export type EventSource =
  | 'browser_sdk'
  | 'server_api'
  | 'worker'
  | 'simulator'
  | 'webhook'
  | 'admin_console';

export type EventType =
  | 'session.started'
  | 'cart.viewed'
  | 'cart.updated'
  | 'checkout.started'
  | 'decision.requested'
  | 'decision.served'
  | 'intervention.exposed'
  | 'intervention.interacted'
  | 'order.completed'
  | 'order.refunded'
  | 'consent.changed'
  | 'config.changed';

// ─────────────────────────────────────────────────────────────────────────────
// Session Events
// ─────────────────────────────────────────────────────────────────────────────

export interface SessionStartedPayload {
  readonly locale: string;
  readonly device_category: DeviceCategory;
  readonly referrer_category: ReferrerCategory;
  readonly user_agent_hash?: string; // Hashed, not raw
  readonly viewport_width?: number;
  readonly viewport_height?: number;
}

export type DeviceCategory = 'mobile' | 'tablet' | 'desktop' | 'unknown';
export type ReferrerCategory =
  | 'direct'
  | 'search'
  | 'social'
  | 'email'
  | 'paid'
  | 'organic'
  | 'unknown';

export type SessionStartedEvent = EventEnvelope<SessionStartedPayload>;

// ─────────────────────────────────────────────────────────────────────────────
// Cart Events
// ─────────────────────────────────────────────────────────────────────────────

export interface CartViewedPayload {
  readonly cart_id_hash: CartIdHash;
  readonly value_minor: number;
  readonly item_count: number;
  readonly currency: Currency;
  readonly items: readonly CartEventItem[];
}

export interface CartEventItem {
  readonly sku: string; // No product names or descriptions
  readonly quantity: number;
  readonly unit_price_minor: number;
  readonly total_minor: number;
  readonly category?: string; // Generic category only
}

export type CartViewedEvent = EventEnvelope<CartViewedPayload>;

export interface CartUpdatedPayload {
  readonly cart_id_hash: CartIdHash;
  readonly change_type: CartChangeType;
  readonly value_minor: number;
  readonly item_count: number;
  readonly currency: Currency;
  readonly items: readonly CartEventItem[];
}

export type CartChangeType =
  | 'item_added'
  | 'item_removed'
  | 'quantity_increased'
  | 'quantity_decreased'
  | 'cart_cleared';

export type CartUpdatedEvent = EventEnvelope<CartUpdatedPayload>;

// ─────────────────────────────────────────────────────────────────────────────
// Checkout Events
// ─────────────────────────────────────────────────────────────────────────────

export interface CheckoutStartedPayload {
  readonly cart_id_hash: CartIdHash;
  readonly cart_value_minor: number;
  readonly checkout_category: CheckoutCategory;
  readonly currency: Currency;
}

export type CheckoutCategory =
  | 'guest'
  | 'registered'
  | 'returning'
  | 'unknown';

export type CheckoutStartedEvent = EventEnvelope<CheckoutStartedPayload>;

// ─────────────────────────────────────────────────────────────────────────────
// Decision Events
// ─────────────────────────────────────────────────────────────────────────────

export interface DecisionRequestedPayload {
  readonly request_id: string;
  readonly page: string;
  readonly cart_id_hash: CartIdHash;
  readonly cart_value_minor: number;
  readonly feature_snapshot_id: string | null;
  readonly eligible_actions: readonly string[];
}

export type DecisionRequestedEvent = EventEnvelope<DecisionRequestedPayload>;

export interface DecisionServedPayload {
  readonly decision_id: DecisionId;
  readonly request_id: string;
  readonly action_type: string;
  readonly policy_version: PolicyVersion;
  readonly model_version: string | null;
  readonly experiment_id: ExperimentId | null;
  readonly experiment_variant: 'control' | 'treatment' | null;
  readonly reason_codes: readonly string[];
  readonly latency_ms: number;
}

export type DecisionServedEvent = EventEnvelope<DecisionServedPayload>;

// ─────────────────────────────────────────────────────────────────────────────
// Intervention Events
// ─────────────────────────────────────────────────────────────────────────────

export interface InterventionExposedPayload {
  readonly decision_id: DecisionId;
  readonly renderer_version: string;
  readonly action_type: string;
  readonly visible_duration_ms?: number;
}

export type InterventionExposedEvent = EventEnvelope<InterventionExposedPayload>;

export interface InterventionInteractedPayload {
  readonly decision_id: DecisionId;
  readonly interaction_type: InteractionType;
  readonly time_to_interaction_ms: number;
}

export type InteractionType =
  | 'accepted'
  | 'dismissed'
  | 'clicked'
  | 'expanded'
  | 'copied_code'
  | 'timeout';

export type InterventionInteractedEvent = EventEnvelope<InterventionInteractedPayload>;

// ─────────────────────────────────────────────────────────────────────────────
// Order Events (Outcomes)
// ─────────────────────────────────────────────────────────────────────────────

export interface OrderCompletedPayload {
  readonly order_hash: string; // SHA-256 of order ID, not the raw ID
  readonly cart_id_hash: CartIdHash;
  readonly decision_id: DecisionId | null;
  readonly revenue_minor: number;
  readonly margin_bucket: MarginBucket; // Bucketed for privacy
  readonly currency: Currency;
  readonly redeemed_incentive: boolean;
  readonly incentive_value_minor?: number;
}

export type MarginBucket =
  | 'negative'
  | 'low' // 0-15%
  | 'medium' // 15-30%
  | 'high' // 30%+
  | 'unknown';

export type OrderCompletedEvent = EventEnvelope<OrderCompletedPayload>;

export interface OrderRefundedPayload {
  readonly order_hash: string;
  readonly decision_id: DecisionId | null;
  readonly refund_value_minor: number;
  readonly refund_reason_category: RefundReasonCategory;
  readonly currency: Currency;
}

export type RefundReasonCategory =
  | 'customer_request'
  | 'quality_issue'
  | 'shipping_issue'
  | 'fraud'
  | 'other'
  | 'unknown';

export type OrderRefundedEvent = EventEnvelope<OrderRefundedPayload>;

// ─────────────────────────────────────────────────────────────────────────────
// Consent Events
// ─────────────────────────────────────────────────────────────────────────────

export interface ConsentChangedPayload {
  readonly allowed_purposes: readonly ConsentPurpose[];
  readonly consent_source: ConsentSource;
  readonly consent_version: string;
  readonly previous_state?: readonly ConsentPurpose[];
}

export type ConsentPurpose =
  | 'analytics'
  | 'personalization'
  | 'marketing';

export type ConsentSource =
  | 'cmp_banner'
  | 'preference_center'
  | 'sdk_api'
  | 'explicit_opt_in'
  | 'explicit_opt_out';

export type ConsentChangedEvent = EventEnvelope<ConsentChangedPayload>;

// ─────────────────────────────────────────────────────────────────────────────
// Configuration Events (Admin Audit)
// ─────────────────────────────────────────────────────────────────────────────

export interface ConfigChangedPayload {
  readonly actor_id: string;
  readonly actor_role: string;
  readonly resource_type: ConfigResourceType;
  readonly resource_id: string;
  readonly action: ConfigAction;
  readonly before_hash: string | null; // SHA-256 of previous state
  readonly after_hash: string; // SHA-256 of new state
  readonly reason?: string;
  readonly approval_id?: string; // For two-person rule changes
}

export type ConfigResourceType =
  | 'policy'
  | 'experiment'
  | 'kill_switch'
  | 'budget'
  | 'integration'
  | 'model'
  | 'feature_flag';

export type ConfigAction =
  | 'created'
  | 'updated'
  | 'activated'
  | 'deactivated'
  | 'deleted'
  | 'approved'
  | 'rejected';

export type ConfigChangedEvent = EventEnvelope<ConfigChangedPayload>;

// ─────────────────────────────────────────────────────────────────────────────
// Type Guards
// ─────────────────────────────────────────────────────────────────────────────

export function isSessionStartedEvent(event: EventEnvelope): event is SessionStartedEvent {
  return event.event_type === 'session.started';
}

export function isCartViewedEvent(event: EventEnvelope): event is CartViewedEvent {
  return event.event_type === 'cart.viewed';
}

export function isCartUpdatedEvent(event: EventEnvelope): event is CartUpdatedEvent {
  return event.event_type === 'cart.updated';
}

export function isCheckoutStartedEvent(event: EventEnvelope): event is CheckoutStartedEvent {
  return event.event_type === 'checkout.started';
}

export function isDecisionRequestedEvent(event: EventEnvelope): event is DecisionRequestedEvent {
  return event.event_type === 'decision.requested';
}

export function isDecisionServedEvent(event: EventEnvelope): event is DecisionServedEvent {
  return event.event_type === 'decision.served';
}

export function isInterventionExposedEvent(event: EventEnvelope): event is InterventionExposedEvent {
  return event.event_type === 'intervention.exposed';
}

export function isInterventionInteractedEvent(event: EventEnvelope): event is InterventionInteractedEvent {
  return event.event_type === 'intervention.interacted';
}

export function isOrderCompletedEvent(event: EventEnvelope): event is OrderCompletedEvent {
  return event.event_type === 'order.completed';
}

export function isOrderRefundedEvent(event: EventEnvelope): event is OrderRefundedEvent {
  return event.event_type === 'order.refunded';
}

export function isConsentChangedEvent(event: EventEnvelope): event is ConsentChangedEvent {
  return event.event_type === 'consent.changed';
}

export function isConfigChangedEvent(event: EventEnvelope): event is ConfigChangedEvent {
  return event.event_type === 'config.changed';
}

// ─────────────────────────────────────────────────────────────────────────────
// Event Validation Helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Check if event contains prohibited data
 * Per MASTER_PROMPT.md Section 7: No name, email, phone, raw order ID, full address,
 * payment data, password, token, or secret
 */
export function containsProhibitedData(event: EventEnvelope): boolean {
  const eventStr = JSON.stringify(event).toLowerCase();

  // Check for common prohibited field patterns
  const prohibitedPatterns = [
    /\b(password|passwd|pwd)\b/,
    /\b(credit[_-]?card|cc[_-]?number)\b/,
    /\b(cvv|cvc|card[_-]?verification)\b/,
    /\b(ssn|social[_-]?security)\b/,
    /\b(api[_-]?key|secret[_-]?key|private[_-]?key)\b/,
    /\b(token|bearer|authorization)\b/,
    /\b(email|e[_-]?mail)["']?\s*:\s*["'][^"']+@/,
    /\b(phone|tel|mobile)["']?\s*:\s*["'][+\d\s()-]+/,
    /\b(address|street|zip|postal)["']?\s*:\s*["'][^"']{10,}/,
  ];

  return prohibitedPatterns.some(pattern => pattern.test(eventStr));
}

/**
 * Validate event envelope structure
 */
export function isValidEventEnvelope(event: unknown): event is EventEnvelope {
  if (typeof event !== 'object' || event === null) return false;

  const e = event as Record<string, unknown>;

  return (
    typeof e.event_id === 'string' &&
    typeof e.event_type === 'string' &&
    typeof e.schema_version === 'string' &&
    typeof e.occurred_at === 'string' &&
    typeof e.tenant_id === 'string' &&
    typeof e.shop_id === 'string' &&
    typeof e.session_id === 'string' &&
    typeof e.source === 'string' &&
    typeof e.trace_id === 'string' &&
    typeof e.payload === 'object' &&
    e.payload !== null
  );
}
