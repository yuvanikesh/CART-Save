/**
 * CartGuard AI - Experimentation Package
 * Per MASTER_PROMPT.md Section 14: Experimentation and Measurement
 *
 * Handles deterministic experiment assignment and tracking.
 */

import type { ExperimentId, SessionId } from '@cartguard/domain';
import { createHash } from 'crypto';

export interface ExperimentAssignment {
  readonly experimentId: ExperimentId;
  readonly variant: 'control' | 'treatment';
  readonly assigned: boolean;
}

/**
 * Deterministically assign a unit to a variant
 * Per MASTER_PROMPT.md Section 14: Randomize deterministically at a stable appropriate unit
 */
export function assignVariant(
  unitId: string,
  experimentId: string,
  allocation: { control: number; treatment: number },
  salt: string
): 'control' | 'treatment' {
  // Hash the unit ID + experiment ID + salt for deterministic assignment
  const hash = createHash('sha256')
    .update(`${unitId}:${experimentId}:${salt}`)
    .digest();

  // Convert first 4 bytes to a number between 0 and 1
  const hashValue = hash.readUInt32BE(0) / 0xffffffff;

  // Assign based on allocation
  return hashValue < allocation.control ? 'control' : 'treatment';
}

/**
 * Check if a unit is eligible for an experiment
 */
export function isEligibleForExperiment(
  sessionId: SessionId,
  experimentId: ExperimentId,
  experimentState: 'draft' | 'active' | 'paused' | 'completed' | 'cancelled'
): boolean {
  return experimentState === 'active';
}
