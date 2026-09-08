/**
 * CartGuard AI - Guardrails Module
 * Per MASTER_PROMPT.md Section 2: Engineering Constitution
 *
 * Pure functions for policy guardrails: margin, budget, frequency caps
 * These are the final safety checks before approving an action
 */

import type {
  Action,
  Cart,
  Policy,
  BudgetState,
  Candidate,
} from './types';

/**
 * Guardrail check result
 */
export interface GuardrailResult {
  readonly passed: boolean;
  readonly reason?: string;
  readonly violatedConstraint?: string;
}

/**
 * Check all guardrails for a candidate action
 * Per MASTER_PROMPT.md Section 9.374-391: Policy budget margin caps
 */
export function applyGuardrails(
  candidate: Candidate,
  cart: Cart,
  policy: Policy,
  budgetState: BudgetState
): GuardrailResult {
  // Check action is in allowed list
  if (!policy.allowedActions.includes(candidate.action.type)) {
    return {
      passed: false,
      reason: 'Action not in policy allowed list',
      violatedConstraint: 'allowed_actions',
    };
  }

  // Check margin floor for monetary actions
  if (isMonetaryAction(candidate.action)) {
    const marginCheck = checkMarginFloor(
      candidate.action,
      cart,
      policy.economics.minimumMarginBps
    );
    if (!marginCheck.passed) {
      return marginCheck;
    }

    // Check budget constraints
    const budgetCheck = checkBudgetConstraints(
      candidate.action,
      budgetState,
      policy.economics
    );
    if (!budgetCheck.passed) {
      return budgetCheck;
    }

    // Check discount limits
    const discountCheck = checkDiscountLimits(
      candidate.action,
      policy.economics
    );
    if (!discountCheck.passed) {
      return discountCheck;
    }
  }

  return { passed: true };
}

/**
 * Check if action involves monetary incentive
 */
export function isMonetaryAction(action: Action): boolean {
  return (
    action.type === 'INCENTIVE_PERCENT' ||
    action.type === 'INCENTIVE_FIXED' ||
    action.type === 'FREE_SHIPPING'
  );
}

/**
 * Check margin floor constraint
 * Per MASTER_PROMPT.md Section 2.54: No incentive below margin floor
 */
export function checkMarginFloor(
  action: Action,
  cart: Cart,
  minimumMarginBps: number
): GuardrailResult {
  let discountMinor = 0;

  if (action.type === 'INCENTIVE_PERCENT') {
    discountMinor = Math.min(
      Math.floor((cart.subtotalMinor * action.percent) / 100),
      action.maxDiscountMinor
    );
  } else if (action.type === 'INCENTIVE_FIXED') {
    discountMinor = action.amountMinor;
  } else if (action.type === 'FREE_SHIPPING') {
    discountMinor = cart.shippingMinor;
  }

  // Calculate margin after discount
  const revenueAfterDiscount = cart.totalMinor - discountMinor;

  // Simplified margin check - in production, would need actual cost data
  // For now, ensure discount doesn't exceed a reasonable percentage of revenue
  const maxDiscountForMargin = Math.floor(
    (cart.totalMinor * (10000 - minimumMarginBps)) / 10000
  );

  if (discountMinor > maxDiscountForMargin) {
    return {
      passed: false,
      reason: `Discount ${discountMinor} exceeds margin floor constraint ${maxDiscountForMargin}`,
      violatedConstraint: 'margin_floor',
    };
  }

  return { passed: true };
}

/**
 * Check budget constraints
 * Per MASTER_PROMPT.md Section 2.54: No incentive beyond budget
 */
export function checkBudgetConstraints(
  action: Action,
  budgetState: BudgetState,
  economics: Policy['economics']
): GuardrailResult {
  let incentiveCost = 0;

  if (action.type === 'INCENTIVE_PERCENT') {
    incentiveCost = action.maxDiscountMinor;
  } else if (action.type === 'INCENTIVE_FIXED') {
    incentiveCost = action.amountMinor;
  } else if (action.type === 'FREE_SHIPPING') {
    incentiveCost = action.savedMinor;
  }

  // Check if cost would exceed available budget
  if (incentiveCost > budgetState.availableMinor) {
    return {
      passed: false,
      reason: `Incentive cost ${incentiveCost} exceeds available budget ${budgetState.availableMinor}`,
      violatedConstraint: 'budget',
    };
  }

  // Check if this would exceed monthly budget
  const projectedSpend = budgetState.monthlySpentMinor + incentiveCost;
  if (projectedSpend > economics.monthlyIncentiveBudgetMinor) {
    return {
      passed: false,
      reason: `Projected spend ${projectedSpend} would exceed monthly budget ${economics.monthlyIncentiveBudgetMinor}`,
      violatedConstraint: 'monthly_budget',
    };
  }

  return { passed: true };
}

/**
 * Check discount limits
 * Per MASTER_PROMPT.md Section 2.54: No incentive above configured maximum
 */
export function checkDiscountLimits(
  action: Action,
  economics: Policy['economics']
): GuardrailResult {
  if (action.type === 'INCENTIVE_PERCENT') {
    if (action.percent > economics.maxDiscountPercent) {
      return {
        passed: false,
        reason: `Discount percent ${action.percent} exceeds maximum ${economics.maxDiscountPercent}`,
        violatedConstraint: 'max_discount_percent',
      };
    }

    if (action.maxDiscountMinor > economics.maxDiscountMinor) {
      return {
        passed: false,
        reason: `Max discount ${action.maxDiscountMinor} exceeds limit ${economics.maxDiscountMinor}`,
        violatedConstraint: 'max_discount_minor',
      };
    }
  } else if (action.type === 'INCENTIVE_FIXED') {
    if (action.amountMinor > economics.maxDiscountMinor) {
      return {
        passed: false,
        reason: `Fixed discount ${action.amountMinor} exceeds maximum ${economics.maxDiscountMinor}`,
        violatedConstraint: 'max_discount_minor',
      };
    }
  }

  return { passed: true };
}

/**
 * Calculate the cost of an action for budget tracking
 */
export function calculateActionCost(action: Action, cart: Cart): number {
  switch (action.type) {
    case 'INCENTIVE_PERCENT':
      return Math.min(
        Math.floor((cart.subtotalMinor * action.percent) / 100),
        action.maxDiscountMinor
      );
    case 'INCENTIVE_FIXED':
      return action.amountMinor;
    case 'FREE_SHIPPING':
      return cart.shippingMinor;
    default:
      return 0; // Non-monetary actions have no cost
  }
}

/**
 * Reserve budget for a monetary action (to be called before serving decision)
 * Returns the amount reserved
 */
export function reserveBudget(
  action: Action,
  cart: Cart,
  budgetState: BudgetState
): number {
  const cost = calculateActionCost(action, cart);

  // In production, this would update Redis atomically
  // Here we just return the amount that should be reserved
  return cost;
}
