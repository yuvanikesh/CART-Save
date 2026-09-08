/**
 * CartGuard AI - Eligibility Module
 * Per MASTER_PROMPT.md Section 9: Decision Orchestration
 *
 * Pure functions for determining decision eligibility
 */

import type {
  Cart,
  Policy,
  KillSwitch,
  FrequencyState,
  BudgetState,
  EligibilityContext,
  NoActionReason,
} from './types';
import { hasPersonalizationConsent } from './consent';

/**
 * Eligibility check result
 */
export interface EligibilityResult {
  readonly eligible: boolean;
  readonly reason: NoActionReason | null;
  readonly details?: string;
}

/**
 * Main eligibility check orchestrator
 * Per MASTER_PROMPT.md Section 9.374-391: Decision sequence pseudocode
 */
export function checkEligibility(context: EligibilityContext): EligibilityResult {
  // 1. Consent check - first blocker
  if (!hasPersonalizationConsent(context.session.consent)) {
    return {
      eligible: false,
      reason: 'CONSENT_MISSING',
      details: 'Personalization consent not granted',
    };
  }

  // 2. Kill switch check
  const killSwitchResult = checkKillSwitches(
    context.killSwitches,
    context.session.tenantId,
    context.session.shopId
  );
  if (!killSwitchResult.eligible) {
    return killSwitchResult;
  }

  // 3. Cart validation
  const cartResult = validateCart(context.cart, context.policy);
  if (!cartResult.eligible) {
    return cartResult;
  }

  // 4. Frequency caps
  const frequencyResult = checkFrequencyCaps(
    context.frequencyState,
    context.policy.frequencyCaps
  );
  if (!frequencyResult.eligible) {
    return frequencyResult;
  }

  // 5. Budget availability
  const budgetResult = checkBudgetAvailability(context.budgetState);
  if (!budgetResult.eligible) {
    return budgetResult;
  }

  return { eligible: true, reason: null };
}

/**
 * Check if any kill switches are active
 * Per MASTER_PROMPT.md Section 2.59: Kill switch scopes
 */
export function checkKillSwitches(
  killSwitches: readonly KillSwitch[],
  tenantId: string,
  shopId: string
): EligibilityResult {
  // Check global kill switch first (highest priority)
  const globalKillSwitch = killSwitches.find(
    (ks) => ks.scope === 'global' && ks.active
  );
  if (globalKillSwitch) {
    return {
      eligible: false,
      reason: 'KILL_SWITCH_ENABLED',
      details: `Global kill switch: ${globalKillSwitch.reason}`,
    };
  }

  // Check tenant-specific kill switch
  const tenantKillSwitch = killSwitches.find(
    (ks) =>
      ks.scope === 'tenant' && ks.resourceId === tenantId && ks.active
  );
  if (tenantKillSwitch) {
    return {
      eligible: false,
      reason: 'KILL_SWITCH_ENABLED',
      details: `Tenant kill switch: ${tenantKillSwitch.reason}`,
    };
  }

  // Check shop-specific kill switch
  const shopKillSwitch = killSwitches.find(
    (ks) => ks.scope === 'shop' && ks.resourceId === shopId && ks.active
  );
  if (shopKillSwitch) {
    return {
      eligible: false,
      reason: 'KILL_SWITCH_ENABLED',
      details: `Shop kill switch: ${shopKillSwitch.reason}`,
    };
  }

  return { eligible: true, reason: null };
}

/**
 * Validate cart meets minimum requirements
 */
export function validateCart(cart: Cart, policy: Policy): EligibilityResult {
  // Check cart has items
  if (cart.items.length === 0) {
    return {
      eligible: false,
      reason: 'CART_INELIGIBLE',
      details: 'Cart is empty',
    };
  }

  // Check cart value is positive
  if (cart.totalMinor <= 0) {
    return {
      eligible: false,
      reason: 'CART_INELIGIBLE',
      details: 'Cart total must be positive',
    };
  }

  // Check currency matches policy
  if (cart.currency !== policy.economics.minimumMarginBps.toString().slice(0, 3)) {
    // Note: This is a simplified check - real implementation would validate currency properly
    // For now, just ensure currency is set
    if (!cart.currency) {
      return {
        eligible: false,
        reason: 'CART_INELIGIBLE',
        details: 'Cart currency not specified',
      };
    }
  }

  return { eligible: true, reason: null };
}

/**
 * Check frequency caps
 * Per MASTER_PROMPT.md Section 2.54: Frequency caps prevent customer fatigue
 */
export function checkFrequencyCaps(
  state: FrequencyState,
  caps: Policy['frequencyCaps']
): EligibilityResult {
  if (state.sessionCount >= caps.perSession) {
    return {
      eligible: false,
      reason: 'FREQUENCY_CAP_EXCEEDED',
      details: `Session cap reached: ${state.sessionCount}/${caps.perSession}`,
    };
  }

  if (state.customer7dCount >= caps.perCustomer7d) {
    return {
      eligible: false,
      reason: 'FREQUENCY_CAP_EXCEEDED',
      details: `7-day cap reached: ${state.customer7dCount}/${caps.perCustomer7d}`,
    };
  }

  if (state.customer30dCount >= caps.perCustomer30d) {
    return {
      eligible: false,
      reason: 'FREQUENCY_CAP_EXCEEDED',
      details: `30-day cap reached: ${state.customer30dCount}/${caps.perCustomer30d}`,
    };
  }

  return { eligible: true, reason: null };
}

/**
 * Check if budget is available for monetary actions
 * Per MASTER_PROMPT.md Section 2.54: No incentive beyond budget
 */
export function checkBudgetAvailability(state: BudgetState): EligibilityResult {
  if (state.availableMinor <= 0) {
    return {
      eligible: false,
      reason: 'BUDGET_EXHAUSTED',
      details: `Monthly budget exhausted: ${state.monthlySpentMinor}/${state.monthlyBudgetMinor}`,
    };
  }

  return { eligible: true, reason: null };
}

/**
 * Check if a specific action type is allowed by policy
 */
export function isActionAllowed(
  actionType: string,
  policy: Policy
): boolean {
  return policy.allowedActions.includes(actionType as any);
}

/**
 * Get minimum cart value for eligibility (can be extended with more rules)
 */
export function getMinimumCartValue(policy: Policy): number {
  // This could be configurable per policy
  // For now, any positive value is acceptable
  return 1;
}
