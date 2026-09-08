/**
 * CartGuard AI - Decisioning Package
 * Per MASTER_PROMPT.md Section 9: Decision Orchestration
 *
 * Application service layer that orchestrates domain logic with adapters.
 * This is the use-case layer that coordinates between domain, persistence,
 * and external services without implementing business constraints directly.
 */

import type {
  Decision,
  DecisionRequest,
  EligibilityContext,
  Session,
  Cart,
  Policy,
  KillSwitch,
  FrequencyState,
  BudgetState,
  Clock,
  IdGenerator,
} from '@cartguard/domain';
import { makeDecision, type DecisionResult } from '@cartguard/domain';
import { createScopedLogger } from '@cartguard/observability';

/**
 * Decision service dependencies (injected)
 */
export interface DecisionServiceDeps {
  readonly clock: Clock;
  readonly idGenerator: IdGenerator;
  readonly fetchSession: (sessionId: string, tenantId: string) => Promise<Session>;
  readonly fetchPolicy: (tenantId: string, shopId: string) => Promise<Policy>;
  readonly fetchKillSwitches: (tenantId: string) => Promise<readonly KillSwitch[]>;
  readonly fetchFrequencyState: (sessionId: string, tenantId: string) => Promise<FrequencyState>;
  readonly fetchBudgetState: (tenantId: string) => Promise<BudgetState>;
  readonly persistDecision: (decision: Decision) => Promise<void>;
  readonly reserveBudget?: (decision: Decision, cart: Cart) => Promise<void>;
}

/**
 * Main decision service
 * Orchestrates the complete decision flow per MASTER_PROMPT.md Section 9.374-391
 */
export class DecisionService {
  constructor(private deps: DecisionServiceDeps) {}

  async decide(request: DecisionRequest): Promise<DecisionResult> {
    const logger = createScopedLogger({
      requestId: request.request_id,
      sessionId: request.session_id,
      traceId: request.request_id, // In production, this comes from request headers
    });

    logger.info('Decision requested');

    try {
      // 1. Fetch context (adapters)
      const [session, policy, killSwitches, frequencyState, budgetState] = await Promise.all([
        this.deps.fetchSession(request.session_id, session.tenantId),
        this.deps.fetchPolicy(session.tenantId, session.shopId),
        this.deps.fetchKillSwitches(session.tenantId),
        this.deps.fetchFrequencyState(request.session_id, session.tenantId),
        this.deps.fetchBudgetState(session.tenantId),
      ]);

      // 2. Build eligibility context
      const context: EligibilityContext = {
        session,
        cart: this.adaptCart(request.cart),
        policy,
        killSwitches,
        frequencyState,
        budgetState,
      };

      // 3. Make decision (pure domain logic)
      const result = makeDecision(context, {
        clock: this.deps.clock,
        idGenerator: this.deps.idGenerator,
        experimentAssignment: null, // Phase 3: Get from experiment service
        featureSnapshotId: null, // Phase 4: Get from feature store
        modelVersion: null, // Phase 4: Get from model service
      });

      // 4. Persist decision atomically with outbox
      await this.deps.persistDecision(result.decision);

      // 5. Reserve budget for monetary actions
      if (result.selectedCandidate.action.type !== 'NO_ACTION' && this.deps.reserveBudget) {
        await this.deps.reserveBudget(result.decision, context.cart);
      }

      logger.info({
        decisionId: result.decision.decisionId,
        action: result.decision.action.type,
        status: result.decision.status,
      }, 'Decision completed');

      return result;
    } catch (error) {
      logger.error({ error }, 'Decision failed');
      throw error;
    }
  }

  private adaptCart(requestCart: any): Cart {
    // Adapt API request format to domain Cart type
    return {
      cartIdHash: requestCart.cart_id_hash,
      subtotalMinor: requestCart.subtotal_minor,
      shippingMinor: requestCart.shipping_minor,
      taxMinor: requestCart.tax_minor || 0,
      totalMinor: requestCart.total_minor,
      currency: requestCart.currency,
      items: requestCart.items.map((item: any) => ({
        sku: item.sku,
        quantity: item.quantity,
        unitPriceMinor: item.unit_price_minor,
        totalMinor: item.total_minor,
      })),
    };
  }
}

export { type DecisionResult };
