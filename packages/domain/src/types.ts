/**
 * CartGuard AI Domain Types
 * Pure TypeScript entities with no framework dependencies
 * Per MASTER_PROMPT.md Section 3 (Domain Vocabulary) and Section 5 (Architecture)
 */

// ─────────────────────────────────────────────────────────────────────────────
// Core Identifiers (branded types for type safety)
// ─────────────────────────────────────────────────────────────────────────────

export type TenantId = string & { readonly __brand: 'TenantId' };
export type ShopId = string & { readonly __brand: 'ShopId' };
export type SessionId = string & { readonly __brand: 'SessionId' };
export type CartIdHash = string & { readonly __brand: 'CartIdHash' };
export type DecisionId = string & { readonly __brand: 'DecisionId' };
export type PolicyVersion = string & { readonly __brand: 'PolicyVersion' };
export type ExperimentId = string & { readonly __brand: 'ExperimentId' };
export type EventId = string & { readonly __brand: 'EventId' };

// ─────────────────────────────────────────────────────────────────────────────
// Tenant and Shop
// ─────────────────────────────────────────────────────────────────────────────

export interface Tenant {
  readonly id: TenantId;
  readonly name: string;
  readonly active: boolean;
  readonly createdAt: Date;
}

export interface Shop {
  readonly id: ShopId;
  readonly tenantId: TenantId;
  readonly origin: string; // Allowed origin for browser SDK
  readonly currency: Currency;
  readonly locale: string;
  readonly active: boolean;
}

export type Currency = 'USD' | 'EUR' | 'GBP' | 'INR';

// ─────────────────────────────────────────────────────────────────────────────
// Session and Consent
// ─────────────────────────────────────────────────────────────────────────────

export interface Session {
  readonly id: SessionId;
  readonly tenantId: TenantId;
  readonly shopId: ShopId;
  readonly consent: ConsentState;
  readonly startedAt: Date;
  readonly locale: string;
}

export interface ConsentState {
  readonly analytics: boolean;
  readonly personalization: boolean;
  readonly marketing: boolean;
  readonly version: string; // Consent snapshot version
}

// ─────────────────────────────────────────────────────────────────────────────
// Cart
// ─────────────────────────────────────────────────────────────────────────────

export interface Cart {
  readonly cartIdHash: CartIdHash;
  readonly subtotalMinor: number; // Amount in minor units (cents)
  readonly shippingMinor: number;
  readonly taxMinor: number;
  readonly totalMinor: number;
  readonly currency: Currency;
  readonly items: readonly CartItem[];
}

export interface CartItem {
  readonly sku: string;
  readonly quantity: number;
  readonly unitPriceMinor: number;
  readonly totalMinor: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Actions (Section 3.79-91: Allowed Action Catalog)
// ─────────────────────────────────────────────────────────────────────────────

export type ActionType =
  | 'NO_ACTION'
  | 'REASSURANCE_MESSAGE'
  | 'SHIPPING_PROGRESS'
  | 'SUPPORT_PROMPT'
  | 'INVENTORY_CLARIFICATION'
  | 'FREE_SHIPPING'
  | 'INCENTIVE_PERCENT'
  | 'INCENTIVE_FIXED'
  | 'SAVE_CART_REMINDER';

export type Action =
  | { readonly type: 'NO_ACTION'; readonly reason: NoActionReason }
  | {
      readonly type: 'REASSURANCE_MESSAGE';
      readonly messageKey: string;
      readonly params?: Record<string, string | number>;
    }
  | {
      readonly type: 'SHIPPING_PROGRESS';
      readonly messageKey: string;
      readonly thresholdMinor: number;
      readonly remainingMinor: number;
    }
  | { readonly type: 'SUPPORT_PROMPT'; readonly messageKey: string }
  | { readonly type: 'INVENTORY_CLARIFICATION'; readonly messageKey: string }
  | {
      readonly type: 'FREE_SHIPPING';
      readonly messageKey: string;
      readonly savedMinor: number;
    }
  | {
      readonly type: 'INCENTIVE_PERCENT';
      readonly percent: number;
      readonly maxDiscountMinor: number;
      readonly expiresAt: Date;
    }
  | {
      readonly type: 'INCENTIVE_FIXED';
      readonly amountMinor: number;
      readonly expiresAt: Date;
    }
  | { readonly type: 'SAVE_CART_REMINDER'; readonly messageKey: string };

export type NoActionReason =
  | 'CONSENT_MISSING'
  | 'KILL_SWITCH_ENABLED'
  | 'CART_INELIGIBLE'
  | 'CONTROL_VARIANT'
  | 'NO_ELIGIBLE_CANDIDATE'
  | 'BUDGET_EXHAUSTED'
  | 'FREQUENCY_CAP_EXCEEDED'
  | 'MARGIN_FLOOR_VIOLATION'
  | 'MODEL_TIMEOUT'
  | 'FEATURES_STALE'
  | 'DEPENDENCY_UNAVAILABLE';

// ─────────────────────────────────────────────────────────────────────────────
// Policy (Section 2: Engineering Constitution, Appendix A.982-999)
// ─────────────────────────────────────────────────────────────────────────────

export interface Policy {
  readonly policyId: string;
  readonly version: PolicyVersion;
  readonly tenantId: TenantId;
  readonly shopId: ShopId;
  readonly active: boolean;
  readonly allowedActions: readonly ActionType[];
  readonly frequencyCaps: FrequencyCaps;
  readonly economics: PolicyEconomics;
  readonly experimentation: ExperimentationConfig;
  readonly fallback: FallbackConfig;
  readonly consent: ConsentRequirements;
  readonly createdAt: Date;
  readonly activatedAt: Date | null;
}

export interface FrequencyCaps {
  readonly perSession: number;
  readonly perCustomer7d: number;
  readonly perCustomer30d: number;
}

export interface PolicyEconomics {
  readonly minimumMarginBps: number; // Basis points (e.g., 2500 = 25%)
  readonly monthlyIncentiveBudgetMinor: number;
  readonly maxDiscountPercent: number;
  readonly maxDiscountMinor: number;
}

export interface ExperimentationConfig {
  readonly requireControl: boolean;
  readonly defaultControlAllocation: number; // 0.0 to 1.0
}

export interface FallbackConfig {
  readonly action: 'NO_ACTION' | 'BASELINE_RANKER';
  readonly when: readonly FallbackTrigger[];
}

export type FallbackTrigger =
  | 'model_unavailable'
  | 'feature_stale'
  | 'budget_store_unavailable'
  | 'redis_timeout'
  | 'kafka_unavailable';

export interface ConsentRequirements {
  readonly requiredPurpose: 'personalization';
}

// ─────────────────────────────────────────────────────────────────────────────
// Decision (Section 9: Decision Orchestration)
// ─────────────────────────────────────────────────────────────────────────────

export interface Decision {
  readonly decisionId: DecisionId;
  readonly sessionId: SessionId;
  readonly tenantId: TenantId;
  readonly shopId: ShopId;
  readonly status: DecisionStatus;
  readonly action: Action;
  readonly reasonCodes: readonly string[];
  readonly policyVersion: PolicyVersion;
  readonly modelVersion: string | null;
  readonly experimentId: ExperimentId | null;
  readonly experimentVariant: ExperimentVariant | null;
  readonly featureSnapshotId: string | null;
  readonly requestedAt: Date;
  readonly decidedAt: Date;
  readonly expiresAt: Date;
  readonly traceId: string;
}

export type DecisionStatus = 'APPROVED' | 'REJECTED' | 'NO_ACTION';

// ─────────────────────────────────────────────────────────────────────────────
// Experiments (Section 14: Experimentation and Measurement)
// ─────────────────────────────────────────────────────────────────────────────

export interface Experiment {
  readonly id: ExperimentId;
  readonly tenantId: TenantId;
  readonly name: string;
  readonly hypothesis: string;
  readonly allocation: ExperimentAllocation;
  readonly metrics: ExperimentMetrics;
  readonly state: ExperimentState;
  readonly startDate: Date | null;
  readonly endDate: Date | null;
  readonly createdBy: string;
  readonly createdAt: Date;
}

export interface ExperimentAllocation {
  readonly control: number; // 0.0 to 1.0
  readonly treatment: number; // 0.0 to 1.0
  readonly unit: 'session' | 'customer';
  readonly salt: string; // For deterministic hashing
}

export type ExperimentVariant = 'control' | 'treatment';

export interface ExperimentMetrics {
  readonly primary: string;
  readonly guardrails: readonly string[];
}

export type ExperimentState =
  | 'draft'
  | 'active'
  | 'paused'
  | 'completed'
  | 'cancelled';

// ─────────────────────────────────────────────────────────────────────────────
// Eligibility and Guardrails (Section 9: Decision Orchestration)
// ─────────────────────────────────────────────────────────────────────────────

export interface EligibilityContext {
  readonly session: Session;
  readonly cart: Cart;
  readonly policy: Policy;
  readonly killSwitches: readonly KillSwitch[];
  readonly frequencyState: FrequencyState;
  readonly budgetState: BudgetState;
}

export interface KillSwitch {
  readonly scope: KillSwitchScope;
  readonly resourceId: string | null; // tenantId, experimentId, actionType, etc.
  readonly active: boolean;
  readonly reason: string;
  readonly activatedAt: Date;
}

export type KillSwitchScope =
  | 'global'
  | 'tenant'
  | 'shop'
  | 'experiment'
  | 'action'
  | 'model';

export interface FrequencyState {
  readonly sessionCount: number;
  readonly customer7dCount: number;
  readonly customer30dCount: number;
}

export interface BudgetState {
  readonly monthlySpentMinor: number;
  readonly monthlyBudgetMinor: number;
  readonly availableMinor: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Candidates (Section 9: Decision Orchestration)
// ─────────────────────────────────────────────────────────────────────────────

export interface Candidate {
  readonly action: Action;
  readonly score: number; // From model or baseline ranker
  readonly source: CandidateSource;
  readonly eligible: boolean;
  readonly eligibilityReasons: readonly string[];
}

export type CandidateSource = 'policy' | 'baseline_ranker' | 'model' | 'bandit';

// ─────────────────────────────────────────────────────────────────────────────
// Audit and Outcomes (Section 10: Persistence)
// ─────────────────────────────────────────────────────────────────────────────

export interface DecisionAudit {
  readonly decisionId: DecisionId;
  readonly tenantId: TenantId;
  readonly sessionId: SessionId;
  readonly request: DecisionRequest;
  readonly response: Decision;
  readonly createdAt: Date;
}

export interface DecisionRequest {
  readonly sessionId: SessionId;
  readonly context: RequestContext;
  readonly cart: Cart;
  readonly requestId: string;
}

export interface RequestContext {
  readonly page: string;
  readonly locale: string;
  readonly currency: Currency;
  readonly consent: ConsentState;
  readonly deviceCategory?: string;
  readonly referrerCategory?: string;
}

export interface Exposure {
  readonly exposureId: string;
  readonly decisionId: DecisionId;
  readonly sessionId: SessionId;
  readonly tenantId: TenantId;
  readonly rendererVersion: string;
  readonly exposedAt: Date;
}

export interface Outcome {
  readonly outcomeId: string;
  readonly decisionId: DecisionId;
  readonly sessionId: SessionId;
  readonly tenantId: TenantId;
  readonly type: OutcomeType;
  readonly orderHash: string | null;
  readonly revenueMinor: number | null;
  readonly marginMinor: number | null;
  readonly refundMinor: number | null;
  readonly occurredAt: Date;
}

export type OutcomeType =
  | 'conversion'
  | 'redemption'
  | 'refund'
  | 'dismissal'
  | 'timeout';

// ─────────────────────────────────────────────────────────────────────────────
// Time and Identity Injection (Section 5.228-237: Coding Standards)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Clock interface for deterministic tests
 * Inject this instead of calling Date.now() or new Date() directly
 */
export interface Clock {
  now(): Date;
  timestamp(): number;
}

/**
 * ID generator interface for deterministic tests
 * Inject this instead of generating UUIDs directly
 */
export interface IdGenerator {
  generateId(): string;
  generateEventId(): EventId;
  generateDecisionId(): DecisionId;
  generateSessionId(): SessionId;
}

/**
 * Random number generator interface for deterministic tests
 * Inject this for experiment assignment, sampling, etc.
 */
export interface RandomGenerator {
  random(): number; // 0.0 to 1.0
  randomInt(min: number, max: number): number;
}
