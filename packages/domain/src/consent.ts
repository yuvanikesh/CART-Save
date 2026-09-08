/**
 * CartGuard AI - Consent Module
 * Per MASTER_PROMPT.md Section 2: No personalization decision without valid consent
 *
 * Pure functions for consent checking - no side effects
 */

import type { ConsentState, Policy } from './types';

/**
 * Check if consent allows personalization decisions
 * Per MASTER_PROMPT.md Section 2.52: No personalization decision without valid consent
 */
export function hasPersonalizationConsent(consent: ConsentState): boolean {
  return consent.personalization === true;
}

/**
 * Check if consent meets policy requirements
 */
export function meetsConsentRequirements(
  consent: ConsentState,
  policy: Policy
): boolean {
  if (policy.consent.requiredPurpose === 'personalization') {
    return hasPersonalizationConsent(consent);
  }
  return false;
}

/**
 * Validate consent state structure
 */
export function isValidConsentState(consent: unknown): consent is ConsentState {
  if (typeof consent !== 'object' || consent === null) return false;

  const c = consent as Record<string, unknown>;

  return (
    typeof c.analytics === 'boolean' &&
    typeof c.personalization === 'boolean' &&
    typeof c.marketing === 'boolean' &&
    typeof c.version === 'string'
  );
}

/**
 * Get consent purposes that are enabled
 */
export function getEnabledPurposes(consent: ConsentState): readonly string[] {
  const purposes: string[] = [];
  if (consent.analytics) purposes.push('analytics');
  if (consent.personalization) purposes.push('personalization');
  if (consent.marketing) purposes.push('marketing');
  return purposes;
}
