/**
 * CartGuard AI - Candidate Generation Module
 * Per MASTER_PROMPT.md Section 9: Decision Orchestration
 *
 * Pure functions for generating and ranking action candidates
 */

import type {
  Action,
  ActionType,
  Cart,
  Policy,
  Candidate,
  NoActionReason,
} from './types';

/**
 * Generate candidates based on policy and cart context
 * Per MASTER_PROMPT.md Section 9.374-391: Generate candidates from policy
 */
export function generateCandidates(
  cart: Cart,
  policy: Policy
): readonly Candidate[] {
  const candidates: Candidate[] = [];

  // Always include NO_ACTION as a fallback candidate
  candidates.push({
    action: { type: 'NO_ACTION', reason: 'NO_ELIGIBLE_CANDIDATE' },
    score: 0,
    source: 'policy',
    eligible: true,
    eligibilityReasons: ['Always available as fallback'],
  });

  // Generate candidates for each allowed action type
  for (const actionType of policy.allowedActions) {
    const candidate = generateCandidateForAction(actionType, cart, policy);
    if (candidate) {
      candidates.push(candidate);
    }
  }

  return candidates;
}

/**
 * Generate a specific candidate for an action type
 */
function generateCandidateForAction(
  actionType: ActionType,
  cart: Cart,
  policy: Policy
): Candidate | null {
  switch (actionType) {
    case 'NO_ACTION':
      // Already included as fallback
      return null;

    case 'REASSURANCE_MESSAGE':
      return {
        action: {
          type: 'REASSURANCE_MESSAGE',
          messageKey: 'reassurance.secure_checkout',
        },
        score: 0.3,
        source: 'policy',
        eligible: true,
        eligibilityReasons: ['Non-monetary, always eligible'],
      };

    case 'SHIPPING_PROGRESS':
      return generateShippingProgressCandidate(cart, policy);

    case 'SUPPORT_PROMPT':
      return {
        action: {
          type: 'SUPPORT_PROMPT',
          messageKey: 'support.help_available',
        },
        score: 0.4,
        source: 'policy',
        eligible: true,
        eligibilityReasons: ['Non-monetary, always eligible'],
      };

    case 'INVENTORY_CLARIFICATION':
      return {
        action: {
          type: 'INVENTORY_CLARIFICATION',
          messageKey: 'inventory.availability',
        },
        score: 0.35,
        source: 'policy',
        eligible: true,
        eligibilityReasons: ['Non-monetary, always eligible'],
      };

    case 'FREE_SHIPPING':
      return generateFreeShippingCandidate(cart, policy);

    case 'INCENTIVE_PERCENT':
      return generatePercentIncentiveCandidate(cart, policy);

    case 'INCENTIVE_FIXED':
      return generateFixedIncentiveCandidate(cart, policy);

    case 'SAVE_CART_REMINDER':
      return {
        action: {
          type: 'SAVE_CART_REMINDER',
          messageKey: 'cart.save_reminder',
        },
        score: 0.25,
        source: 'policy',
        eligible: true,
        eligibilityReasons: ['Non-monetary, always eligible'],
      };

    default:
      return null;
  }
}

/**
 * Generate shipping progress candidate
 * Show progress toward free shipping threshold
 */
function generateShippingProgressCandidate(
  cart: Cart,
  policy: Policy
): Candidate | null {
  // Example: $50 free shipping threshold
  const freeShippingThreshold = 5000; // 50.00 in minor units
  const remaining = freeShippingThreshold - cart.subtotalMinor;

  if (remaining > 0 && remaining <= 2000) {
    // Only show if within $20 of threshold
    return {
      action: {
        type: 'SHIPPING_PROGRESS',
        messageKey: 'shipping.threshold_near',
        thresholdMinor: freeShippingThreshold,
        remainingMinor: remaining,
      },
      score: 0.6,
      source: 'policy',
      eligible: true,
      eligibilityReasons: ['Near shipping threshold'],
    };
  }

  return null;
}

/**
 * Generate free shipping candidate
 */
function generateFreeShippingCandidate(
  cart: Cart,
  policy: Policy
): Candidate | null {
  if (cart.shippingMinor > 0) {
    return {
      action: {
        type: 'FREE_SHIPPING',
        messageKey: 'shipping.free_offer',
        savedMinor: cart.shippingMinor,
      },
      score: 0.7,
      source: 'policy',
      eligible: true,
      eligibilityReasons: ['Has shipping cost to waive'],
    };
  }

  return null;
}

/**
 * Generate percent incentive candidate
 */
function generatePercentIncentiveCandidate(
  cart: Cart,
  policy: Policy
): Candidate | null {
  const percent = Math.min(10, policy.economics.maxDiscountPercent);
  const maxDiscountMinor = Math.min(
    Math.floor((cart.subtotalMinor * percent) / 100),
    policy.economics.maxDiscountMinor
  );

  if (maxDiscountMinor > 0) {
    const expiresAt = new Date(Date.now() + 30 * 60 * 1000); // 30 minutes

    return {
      action: {
        type: 'INCENTIVE_PERCENT',
        percent,
        maxDiscountMinor,
        expiresAt,
      },
      score: 0.8,
      source: 'policy',
      eligible: true,
      eligibilityReasons: ['Monetary incentive within limits'],
    };
  }

  return null;
}

/**
 * Generate fixed incentive candidate
 */
function generateFixedIncentiveCandidate(
  cart: Cart,
  policy: Policy
): Candidate | null {
  // Offer a reasonable fixed discount (e.g., $5 off)
  const amountMinor = Math.min(500, policy.economics.maxDiscountMinor);

  if (amountMinor > 0 && cart.subtotalMinor >= amountMinor * 2) {
    // Only if cart is at least 2x the discount
    const expiresAt = new Date(Date.now() + 30 * 60 * 1000); // 30 minutes

    return {
      action: {
        type: 'INCENTIVE_FIXED',
        amountMinor,
        expiresAt,
      },
      score: 0.75,
      source: 'policy',
      eligible: true,
      eligibilityReasons: ['Fixed discount within limits'],
    };
  }

  return null;
}

/**
 * Baseline ranking function
 * Per MASTER_PROMPT.md Section 13: Start with deterministic baseline
 */
export function rankCandidatesBaseline(
  candidates: readonly Candidate[]
): readonly Candidate[] {
  // Sort by score descending (higher score = better candidate)
  return [...candidates].sort((a, b) => b.score - a.score);
}

/**
 * Filter candidates to only eligible ones
 */
export function filterEligibleCandidates(
  candidates: readonly Candidate[]
): readonly Candidate[] {
  return candidates.filter((c) => c.eligible);
}

/**
 * Get the top candidate (first in ranked list)
 */
export function selectTopCandidate(
  candidates: readonly Candidate[]
): Candidate | null {
  const eligible = filterEligibleCandidates(candidates);
  if (eligible.length === 0) return null;

  const ranked = rankCandidatesBaseline(eligible);
  return ranked[0] || null;
}

/**
 * Get NO_ACTION candidate with specific reason
 */
export function noActionCandidate(reason: NoActionReason): Candidate {
  return {
    action: { type: 'NO_ACTION', reason },
    score: 0,
    source: 'policy',
    eligible: true,
    eligibilityReasons: [`Fallback: ${reason}`],
  };
}
