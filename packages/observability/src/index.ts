/**
 * CartGuard AI - Observability Package
 * Per MASTER_PROMPT.md Section 16: Telemetry and Observability
 *
 * Handles structured logging, trace propagation, and redaction of PII.
 */

import pino from 'pino';

export interface LogContext {
  readonly tenantId?: string;
  readonly sessionId?: string;
  readonly traceId?: string;
  readonly decisionId?: string;
  readonly requestId?: string;
}

/**
 * Redacts sensitive information from log messages
 * Per MASTER_PROMPT.md Section 5.235: Redact secrets and PII before any log emission
 */
function redactPII(message: string): string {
  const prohibitedPatterns = [
    /\b[\w\.-]+@[\w\.-]+\.\w{2,4}\b/gi, // Emails
    /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/g, // Credit cards
    /\b(password|secret|token|apiKey)\s*[:=]\s*[^,\s]+/gi, // Secrets
  ];

  let redacted = message;
  for (const pattern of prohibitedPatterns) {
    redacted = redacted.replace(pattern, '[REDACTED]');
  }
  return redacted;
}

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  // Redaction is handled by a custom formatter in production,
  // but we provide the utility here for consistency.
  mixin() {
    return {
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development',
    };
  },
});

export function createScopedLogger(context: LogContext) {
  return logger.child(context);
}

export { redactPII };
