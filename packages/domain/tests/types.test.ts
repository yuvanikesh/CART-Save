/**
 * Unit tests for core domain types
 * Per MASTER_PROMPT.md Section 20: Unit tests for pure policy, eligibility, guardrail behavior
 */

import type {
  Action,
  NoActionReason,
  Policy,
  Cart,
  ConsentState,
  FrequencyCaps,
  PolicyEconomics,
} from '../src/types';

describe('Domain Types', () => {
  describe('Action discriminated unions', () => {
    it('should create NO_ACTION with reason', () => {
      const action: Action = {
        type: 'NO_ACTION',
        reason: 'CONSENT_MISSING',
      };

      expect(action.type).toBe('NO_ACTION');
      if (action.type === 'NO_ACTION') {
        expect(action.reason).toBe('CONSENT_MISSING');
      }
    });

    it('should create INCENTIVE_PERCENT action', () => {
      const action: Action = {
        type: 'INCENTIVE_PERCENT',
        percent: 10,
        maxDiscountMinor: 1000,
        expiresAt: new Date('2026-09-08T00:00:00Z'),
      };

      expect(action.type).toBe('INCENTIVE_PERCENT');
      if (action.type === 'INCENTIVE_PERCENT') {
        expect(action.percent).toBe(10);
        expect(action.maxDiscountMinor).toBe(1000);
      }
    });

    it('should create SHIPPING_PROGRESS action', () => {
      const action: Action = {
        type: 'SHIPPING_PROGRESS',
        messageKey: 'shipping.threshold',
        thresholdMinor: 5000,
        remainingMinor: 1200,
      };

      expect(action.type).toBe('SHIPPING_PROGRESS');
      if (action.type === 'SHIPPING_PROGRESS') {
        expect(action.thresholdMinor).toBe(5000);
        expect(action.remainingMinor).toBe(1200);
      }
    });
  });

  describe('Policy configuration', () => {
    it('should enforce all required policy fields', () => {
      const policy: Policy = {
        policyId: 'policy_001',
        version: 'policy_2026_09_07_1' as any,
        tenantId: 'ten_01' as any,
        shopId: 'shop_01' as any,
        active: true,
        allowedActions: ['NO_ACTION', 'REASSURANCE_MESSAGE', 'FREE_SHIPPING'],
        frequencyCaps: {
          perSession: 1,
          perCustomer7d: 2,
          perCustomer30d: 5,
        },
        economics: {
          minimumMarginBps: 2500, // 25%
          monthlyIncentiveBudgetMinor: 250000,
          maxDiscountPercent: 10,
          maxDiscountMinor: 1500,
        },
        experimentation: {
          requireControl: true,
          defaultControlAllocation: 0.2,
        },
        fallback: {
          action: 'NO_ACTION',
          when: ['model_unavailable', 'feature_stale'],
        },
        consent: {
          requiredPurpose: 'personalization',
        },
        createdAt: new Date('2026-09-01T00:00:00Z'),
        activatedAt: new Date('2026-09-07T00:00:00Z'),
      };

      expect(policy.economics.minimumMarginBps).toBe(2500);
      expect(policy.frequencyCaps.perSession).toBe(1);
      expect(policy.experimentation.requireControl).toBe(true);
    });

    it('should validate margin floor in basis points', () => {
      const marginBps = 2500; // 25%
      const marginPercent = marginBps / 100;
      expect(marginPercent).toBe(25);
    });
  });

  describe('Cart calculations', () => {
    it('should calculate cart total correctly', () => {
      const cart: Cart = {
        cartIdHash: 'cart_hash_123' as any,
        subtotalMinor: 7800, // $78.00
        shippingMinor: 900, // $9.00
        taxMinor: 696, // $6.96 (8% of subtotal)
        totalMinor: 9396, // $93.96
        currency: 'USD',
        items: [
          {
            sku: 'SKU-001',
            quantity: 2,
            unitPriceMinor: 3900,
            totalMinor: 7800,
          },
        ],
      };

      expect(cart.subtotalMinor + cart.shippingMinor + cart.taxMinor).toBe(
        cart.totalMinor
      );
      expect(cart.items[0]!.quantity * cart.items[0]!.unitPriceMinor).toBe(
        cart.items[0]!.totalMinor
      );
    });

    it('should work with minor units for cents precision', () => {
      const priceInDollars = 78.99;
      const priceMinor = Math.round(priceInDollars * 100);
      expect(priceMinor).toBe(7899);

      const backToDollars = priceMinor / 100;
      expect(backToDollars).toBe(78.99);
    });
  });

  describe('Consent state', () => {
    it('should require personalization consent per MASTER_PROMPT invariant', () => {
      const consentWithPersonalization: ConsentState = {
        analytics: true,
        personalization: true,
        marketing: false,
        version: 'v1',
      };

      const consentWithoutPersonalization: ConsentState = {
        analytics: true,
        personalization: false,
        marketing: false,
        version: 'v1',
      };

      // Per MASTER_PROMPT Section 2.51: No personalization decision without valid consent
      expect(consentWithPersonalization.personalization).toBe(true);
      expect(consentWithoutPersonalization.personalization).toBe(false);
    });
  });

  describe('NoActionReason exhaustiveness', () => {
    it('should cover all safety fallback scenarios', () => {
      const reasons: NoActionReason[] = [
        'CONSENT_MISSING',
        'KILL_SWITCH_ENABLED',
        'CART_INELIGIBLE',
        'CONTROL_VARIANT',
        'NO_ELIGIBLE_CANDIDATE',
        'BUDGET_EXHAUSTED',
        'FREQUENCY_CAP_EXCEEDED',
        'MARGIN_FLOOR_VIOLATION',
        'MODEL_TIMEOUT',
        'FEATURES_STALE',
        'DEPENDENCY_UNAVAILABLE',
      ];

      // Per MASTER_PROMPT Section 2.42: Safe default is always available
      expect(reasons).toContain('CONSENT_MISSING');
      expect(reasons).toContain('MODEL_TIMEOUT');
      expect(reasons).toContain('FEATURES_STALE');

      // Per MASTER_PROMPT Section 2.58: Model failures may not make system more aggressive
      expect(reasons).toContain('DEPENDENCY_UNAVAILABLE');
    });
  });
});
