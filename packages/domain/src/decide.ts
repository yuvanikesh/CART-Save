/**
 * CartGuard AI - Decision Module
 * Per MASTER_PROMPT.md Section 9: Decision Orchestration
 *
 * Pure functions for the complete decision flow
 */

import type {
  Decision,
  DecisionId,
  DecisionStatus,
  EligibilityContext,
  Cart,
  Policy,
  Candidate,
  BudgetState,
  Clock,
  IdGenerator,
} from './types';
import { checkEligibility } from './eligibility';
import { generateCandidates, selectTopCandidate, noActionCandidate } from './candidates';
import { applyGuardrails } from './guardrails';

/**
 * Decision orchestration result
 */
export interface DecisionResult {
  readonly decision: Decision;
  readonly selectedCandidate: Candidate;
  readonly allCandidates: readonly Candidate[];
}

/**
 * Decision orchestration dependencies (injected for testing)
 */
export interface DecisionDependencies {
  readonly clock: Clock;
  readonly idGenerator: IdGenerator;
  readonly experimentAssignment?: 'control' | 'treatment' | null;
  readonly featureSnapshotId?: string | null;
  readonly modelVersion?: string | null;
}

/**
 * Main decision orchestration function
 * Per MASTER_PROMPT.md Section 9.374-391: Decision sequence pseudocode
 *
 * Orchestrates the complete decision flow:
 * 1. Check eligibility (consent, kill switches, cart validation, frequency, budget)
 * 2. Check experiment assignment - return NO_ACTION if control
 * 3. Generate candidate actions
 * 4. Rank candidates (baseline or model)
 * 5. Apply guardrails to top candidate
 * 6. Return decision or safe fallback
 */
export function makeDecision(
  context: EligibilityContext,
  deps: DecisionDependencies
): DecisionResult {
  const { clock, idGenerator, experimentAssignment, featureSnapshotId, modelVersion } = deps;

  // 1. Check eligibility
  const eligibilityResult = checkEligibility(context);
  if (!eligibilityResult.eligible) {
    const candidate = noActionCandidate(eligibilityResult.reason!);
    const decision = createDecision(
      context,
      candidate,
      [eligibilityResult.reason!],
      deps
    );
    return {
      decision,
      selectedCandidate: candidate,
      allCandidates: [candidate],
    };
  }

  // 2. Check experiment assignment - control gets NO_ACTION
  if (experimentAssignment === 'control') {
    const candidate = noActionCandidate('CONTROL_VARIANT');
    const decision = createDecision(
      context,
      candidate,
      ['CONTROL_VARIANT'],
      deps
    );
    return {
      decision,
      selectedCandidate: candidate,
      allCandidates: [candidate],
    };
  }

  // 3. Generate candidates
  const allCandidates = generateCandidates(context.cart, context.policy);

  // 4. Rank candidates (baseline for now - model ranking in Phase 4)
  // 5. Select top candidate
  let selectedCandidate = selectTopCandidate(allCandidates);

  // 6. Apply guardrails to selected candidate
  if (selectedCandidate && selectedCandidate.action.type !== 'NO_ACTION') {
    const guardrailResult = applyGuardrails(
      selectedCandidate,
      context.cart,
      context.policy,
      context.budgetState
    );

    if (!guardrailResult.passed) {
      // Guardrail failed - fall back to NO_ACTION
      selectedCandidate = noActionCandidate('NO_ELIGIBLE_CANDIDATE');
      const decision = createDecision(
        context,
        selectedCandidate,
        ['GUARDRAIL_FAILED', guardrailResult.violatedConstraint || 'unknown'],
        deps
      );
      return {
        decision,
        selectedCandidate,
        allCandidates,
      };
    }
  }

  // 7. Create final decision
  if (!selectedCandidate) {
    selectedCandidate = noActionCandidate('NO_ELIGIBLE_CANDIDATE');
  }

  const decision = createDecision(
    context,
    selectedCandidate,
    [selectedCandidate.action.type === 'NO_ACTION' ? 'NO_ACTION' : 'APPROVED'],
    deps
  );

  return {
    decision,
    selectedCandidate,
    allCandidates,
  };
}

/**
 * Create a Decision entity from the selected candidate
 * Per MASTER_PROMPT.md Section 2.56: Immutable decision audit
 */
function createDecision(
  context: EligibilityContext,
  candidate: Candidate,
  reasonCodes: readonly string[],
  deps: DecisionDependencies
): Decision {
  const { clock, idGenerator, experimentAssignment, featureSnapshotId, modelVersion } = deps;

  const now = clock.now();
  const expiresAt = new Date(now.getTime() + 15 * 60 * 1000); // 15 minutes expiry

  const status: DecisionStatus =
    candidate.action.type === 'NO_ACTION' ? 'NO_ACTION' : 'APPROVED';

  return {
    decisionId: idGenerator.generateDecisionId(),
    sessionId: context.session.id,
    tenantId: context.session.tenantId,
    shopId: context.session.shopId,
    status,
    action: candidate.action,
    reasonCodes: [...reasonCodes],
    policyVersion: context.policy.version,
    modelVersion: modelVersion || null,
    experimentId: null, // Set by experiment service in application layer
    experimentVariant: experimentAssignment || null,
    featureSnapshotId: featureSnapshotId || null,
    requestedAt: now,
    decidedAt: now,
    expiresAt,
    traceId: idGenerator.generateId(), // Trace ID should come from request context
  };
}

/**
 * Validate decision before returning to client
 */
export function validateDecision(decision: Decision): boolean {
  return (
    !!decision.decisionId &&
    !!decision.sessionId &&
    !!decision.tenantId &&
    !!decision.shopId &&
    !!decision.status &&
    !!decision.action &&
    !!decision.policyVersion &&
    decision.reasonCodes.length > 0 &&
    decision.decidedAt <= decision.expiresAt
  );
}
