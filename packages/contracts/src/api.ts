/**
 * CartGuard AI API Contracts
 * Per MASTER_PROMPT.md Section 8: API Contracts
 *
 * All public APIs use HTTPS, explicit major versioning, JSON schemas,
 * request IDs, rate limits, and structured errors.
 */

import type {
  TenantId,
  ShopId,
  SessionId,
  CartIdHash,
  DecisionId,
  PolicyVersion,
  ExperimentId,
  Currency,
  ConsentState,
  Action,
  ActionType,
} from '@cartguard/domain';

// ─────────────────────────────────────────────────────────────────────────────
// Decision API: POST /v1/decisions
// ─────────────────────────────────────────────────────────────────────────────

export interface DecisionRequest {
  readonly request_id: string;
  readonly session_id: SessionId;
  readonly context: DecisionContext;
  readonly cart: DecisionCart;
}

export interface DecisionContext {
  readonly page: string; // 'cart', 'checkout', 'product', etc.
  readonly locale: string; // e.g., 'en-US'
  readonly currency: Currency;
  readonly consent: ConsentState;
  readonly device_category?: 'mobile' | 'tablet' | 'desktop';
  readonly referrer_category?: string;
}

export interface DecisionCart {
  readonly cart_id_hash: CartIdHash;
  readonly subtotal_minor: number;
  readonly shipping_minor: number;
  readonly tax_minor?: number;
  readonly total_minor: number;
  readonly items: readonly DecisionCartItem[];
}

export interface DecisionCartItem {
  readonly sku: string;
  readonly quantity: number;
  readonly unit_price_minor: number;
  readonly total_minor: number;
  readonly category?: string;
}

export interface DecisionResponse {
  readonly decision_id: DecisionId;
  readonly status: DecisionResponseStatus;
  readonly action: Action;
  readonly reason_codes: readonly string[];
  readonly policy_version: PolicyVersion;
  readonly model_version: string | null;
  readonly experiment_id: ExperimentId | null;
  readonly experiment_variant: 'control' | 'treatment' | null;
  readonly expires_at: string; // ISO 8601 timestamp
  readonly trace_id: string;
}

export type DecisionResponseStatus = 'APPROVED' | 'REJECTED' | 'NO_ACTION';

// ─────────────────────────────────────────────────────────────────────────────
// Event API: POST /v1/events:batch
// ─────────────────────────────────────────────────────────────────────────────

export interface BatchEventRequest {
  readonly events: readonly EventBatchItem[];
}

export interface EventBatchItem {
  readonly event_id: string;
  readonly event_type: string;
  readonly schema_version: string;
  readonly occurred_at: string; // ISO 8601 timestamp
  readonly session_id: SessionId;
  readonly payload: Record<string, unknown>;
}

export interface BatchEventResponse {
  readonly results: readonly EventBatchResult[];
  readonly received_at: string;
  readonly trace_id: string;
}

export interface EventBatchResult {
  readonly event_id: string;
  readonly status: EventBatchStatus;
  readonly message?: string;
}

export type EventBatchStatus =
  | 'accepted'
  | 'duplicate'
  | 'rejected'
  | 'retryable';

// ─────────────────────────────────────────────────────────────────────────────
// Health & Status
// ─────────────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  readonly status: 'healthy' | 'degraded' | 'unhealthy';
  readonly timestamp: string;
  readonly version: string;
  readonly dependencies: readonly DependencyHealth[];
}

export interface DependencyHealth {
  readonly name: string;
  readonly status: 'up' | 'down' | 'degraded';
  readonly latency_ms?: number;
  readonly message?: string;
}

export interface ReadinessResponse {
  readonly ready: boolean;
  readonly timestamp: string;
  readonly checks: readonly ReadinessCheck[];
}

export interface ReadinessCheck {
  readonly name: string;
  readonly ready: boolean;
  readonly message?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Error Response (RFC 7807 Problem Details)
// ─────────────────────────────────────────────────────────────────────────────

export interface ErrorResponse {
  readonly type: string; // URI reference identifying the problem type
  readonly title: string; // Human-readable summary
  readonly status: number; // HTTP status code
  readonly detail?: string; // Human-readable explanation
  readonly instance?: string; // URI reference identifying the specific occurrence
  readonly trace_id: string;
  readonly errors?: readonly ValidationError[]; // For validation failures
}

export interface ValidationError {
  readonly field: string;
  readonly code: string;
  readonly message: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Common Headers
// ─────────────────────────────────────────────────────────────────────────────

export interface CommonRequestHeaders {
  readonly 'X-Request-ID': string;
  readonly 'X-Tenant-Key': string; // Publishable key for browser SDK
  readonly 'X-Trace-ID'?: string;
  readonly 'Origin': string; // Required for browser requests
}

export interface CommonResponseHeaders {
  readonly 'X-Request-ID': string;
  readonly 'X-Trace-ID': string;
  readonly 'X-RateLimit-Limit': string;
  readonly 'X-RateLimit-Remaining': string;
  readonly 'X-RateLimit-Reset': string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Policy API (Merchant/Admin endpoints)
// ─────────────────────────────────────────────────────────────────────────────

export interface PolicyResponse {
  readonly policy_id: string;
  readonly version: PolicyVersion;
  readonly tenant_id: TenantId;
  readonly shop_id: ShopId;
  readonly active: boolean;
  readonly allowed_actions: readonly ActionType[];
  readonly frequency_caps: {
    readonly per_session: number;
    readonly per_customer_7d: number;
    readonly per_customer_30d: number;
  };
  readonly economics: {
    readonly minimum_margin_bps: number;
    readonly monthly_incentive_budget_minor: number;
    readonly max_discount_percent: number;
    readonly max_discount_minor: number;
  };
  readonly created_at: string;
  readonly activated_at: string | null;
}

export interface PolicyCreateRequest {
  readonly shop_id: ShopId;
  readonly allowed_actions: readonly ActionType[];
  readonly frequency_caps: {
    readonly per_session: number;
    readonly per_customer_7d: number;
    readonly per_customer_30d: number;
  };
  readonly economics: {
    readonly minimum_margin_bps: number;
    readonly monthly_incentive_budget_minor: number;
    readonly max_discount_percent: number;
    readonly max_discount_minor: number;
  };
  readonly reason?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Experiment API
// ─────────────────────────────────────────────────────────────────────────────

export interface ExperimentResponse {
  readonly id: ExperimentId;
  readonly tenant_id: TenantId;
  readonly name: string;
  readonly hypothesis: string;
  readonly state: 'draft' | 'active' | 'paused' | 'completed' | 'cancelled';
  readonly allocation: {
    readonly control: number;
    readonly treatment: number;
    readonly unit: 'session' | 'customer';
  };
  readonly metrics: {
    readonly primary: string;
    readonly guardrails: readonly string[];
  };
  readonly start_date: string | null;
  readonly end_date: string | null;
  readonly created_at: string;
}

export interface ExperimentCreateRequest {
  readonly name: string;
  readonly hypothesis: string;
  readonly allocation: {
    readonly control: number;
    readonly treatment: number;
    readonly unit: 'session' | 'customer';
  };
  readonly metrics: {
    readonly primary: string;
    readonly guardrails: readonly string[];
  };
  readonly duration_days?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Kill Switch API
// ─────────────────────────────────────────────────────────────────────────────

export interface KillSwitchResponse {
  readonly scope: 'global' | 'tenant' | 'shop' | 'experiment' | 'action' | 'model';
  readonly resource_id: string | null;
  readonly active: boolean;
  readonly reason: string;
  readonly activated_at: string;
  readonly activated_by: string;
}

export interface KillSwitchActivateRequest {
  readonly scope: 'global' | 'tenant' | 'shop' | 'experiment' | 'action' | 'model';
  readonly resource_id?: string;
  readonly reason: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Audit API
// ─────────────────────────────────────────────────────────────────────────────

export interface DecisionAuditResponse {
  readonly decision_id: DecisionId;
  readonly tenant_id: TenantId;
  readonly session_id: SessionId;
  readonly request: DecisionRequest;
  readonly response: DecisionResponse;
  readonly created_at: string;
}

export interface DecisionAuditQuery {
  readonly tenant_id?: TenantId;
  readonly session_id?: SessionId;
  readonly decision_id?: DecisionId;
  readonly start_date?: string;
  readonly end_date?: string;
  readonly limit?: number;
  readonly cursor?: string;
}

export interface AuditQueryResponse<T> {
  readonly results: readonly T[];
  readonly next_cursor?: string;
  readonly total?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Report API
// ─────────────────────────────────────────────────────────────────────────────

export interface ReportRequest {
  readonly report_type: ReportType;
  readonly tenant_id: TenantId;
  readonly start_date: string;
  readonly end_date: string;
  readonly filters?: Record<string, unknown>;
  readonly group_by?: readonly string[];
}

export type ReportType =
  | 'experiment_results'
  | 'decision_distribution'
  | 'budget_utilization'
  | 'conversion_funnel'
  | 'intervention_performance';

export interface ReportResponse {
  readonly report_id: string;
  readonly report_type: ReportType;
  readonly generated_at: string;
  readonly freshness: string; // e.g., "within 5 minutes", "15 minutes stale"
  readonly methodology: string;
  readonly sample_size: number;
  readonly date_range: {
    readonly start: string;
    readonly end: string;
  };
  readonly metrics: Record<string, ReportMetric>;
  readonly caveats: readonly string[];
}

export interface ReportMetric {
  readonly value: number;
  readonly confidence_interval?: [number, number];
  readonly unit?: string;
  readonly comparison?: {
    readonly baseline: number;
    readonly change_percent: number;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Type Guards and Validation
// ─────────────────────────────────────────────────────────────────────────────

export function isDecisionRequest(obj: unknown): obj is DecisionRequest {
  if (typeof obj !== 'object' || obj === null) return false;
  const req = obj as Record<string, unknown>;
  return (
    typeof req.request_id === 'string' &&
    typeof req.session_id === 'string' &&
    typeof req.context === 'object' &&
    typeof req.cart === 'object'
  );
}

export function isErrorResponse(obj: unknown): obj is ErrorResponse {
  if (typeof obj !== 'object' || obj === null) return false;
  const err = obj as Record<string, unknown>;
  return (
    typeof err.type === 'string' &&
    typeof err.title === 'string' &&
    typeof err.status === 'number' &&
    typeof err.trace_id === 'string'
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Rate Limiting
// ─────────────────────────────────────────────────────────────────────────────

export interface RateLimitInfo {
  readonly limit: number;
  readonly remaining: number;
  readonly reset: number; // Unix timestamp
  readonly window_ms: number;
}

export function parseRateLimitHeaders(headers: Record<string, string>): RateLimitInfo | null {
  const limit = headers['X-RateLimit-Limit'];
  const remaining = headers['X-RateLimit-Remaining'];
  const reset = headers['X-RateLimit-Reset'];

  if (!limit || !remaining || !reset) return null;

  return {
    limit: parseInt(limit, 10),
    remaining: parseInt(remaining, 10),
    reset: parseInt(reset, 10),
    window_ms: 60000, // Default 1 minute window
  };
}
