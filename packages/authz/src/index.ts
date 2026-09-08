/**
 * CartGuard AI - Authorization Package
 * Per MASTER_PROMPT.md Section 15: Security, Privacy, and Compliance
 *
 * Enforces tenant isolation and RBAC.
 */

import type { TenantId, ShopId } from '@cartguard/domain';

export interface AuthContext {
  readonly tenantId: TenantId;
  readonly userId: string;
  readonly role: UserRole;
}

export type UserRole =
  | 'Viewer'
  | 'Analyst'
  | 'Experimenter'
  | 'PolicyManager'
  | 'Operator'
  | 'TenantAdmin'
  | 'SecurityAdmin'
  | 'PlatformAdmin';

/**
 * Verifies that a resource belongs to the authenticated tenant
 * Per MASTER_PROMPT.md Section 2.59: No cross-tenant read or write
 */
export function verifyTenantOwnership(
  resourceTenantId: string,
  authContext: AuthContext
): void {
  if (resourceTenantId !== authContext.tenantId) {
    throw new Error(`Tenant isolation breach: Resource ${resourceTenantId} does not belong to tenant ${authContext.tenantId}`);
  }
}

/**
 * Check if a role has permission to perform an action
 * Per MASTER_PROMPT.md Section 27: Merchant administration and separation of duties
 */
export function checkRolePermission(
  role: UserRole,
  action: string
): boolean {
  const permissions: Record<UserRole, string[]> = {
    'Viewer': ['read:reports', 'read:config'],
    'Analyst': ['read:reports', 'read:config', 'create:saved_views'],
    'Experimenter': ['read:reports', 'read:config', 'manage:experiments'],
    'PolicyManager': ['read:reports', 'read:config', 'draft:policies'],
    'Operator': ['read:reports', 'read:config', 'activate:kill_switches'],
    'TenantAdmin': ['manage:tenant', 'manage:memberships', 'manage:integrations'],
    'SecurityAdmin': ['read:audit', 'conduct:security_review'],
    'PlatformAdmin': ['manage:infrastructure', 'break_glass:ops'],
  };

  return permissions[role]?.includes(action) ?? false;
}
