// ============================================================================
//
// Pure password-recovery state rules shared by the auth store and UI.
// ============================================================================

export interface RecoveryCallbackState {
  errorCode: string | null;
  errorDescription: string | null;
}

export const MINIMUM_RECOVERY_PASSWORD_LENGTH = 8;

/** Preserve repeated sign-in events only for the same verified recovery session. */
export function shouldClearRecoveryForAuthEvent(
  event: string,
  recoveryAccessToken: string | null,
  sessionAccessToken: string | null,
): boolean {
  if (event === 'SIGNED_OUT') return true;
  if (event !== 'SIGNED_IN') return false;
  return recoveryAccessToken === null || sessionAccessToken !== recoveryAccessToken;
}

function callbackParameters(value: string): URLSearchParams {
  return new URLSearchParams(value.replace(/^[?#]/, ''));
}

/** Read only callback errors; access/refresh tokens never escape. */
export function parseRecoveryCallback(search: string, hash: string): RecoveryCallbackState {
  const query = callbackParameters(search);
  const fragment = callbackParameters(hash);
  const errorCode = query.get('error_code') ?? fragment.get('error_code')
    ?? query.get('error') ?? fragment.get('error');
  const errorDescription = query.get('error_description')
    ?? fragment.get('error_description');

  if (errorCode || errorDescription) {
    return {
      errorCode,
      errorDescription,
    };
  }

  // URL parameters are never recovery authorization. Only the verified
  // PASSWORD_RECOVERY event from supabase-js can grant the reset form access.
  return {
    errorCode: null,
    errorDescription: null,
  };
}

/** Client guidance; Supabase remains authoritative for hosted password policy. */
export function validateRecoveryPassword(password: string, confirmation: string): string | null {
  if (password.length < MINIMUM_RECOVERY_PASSWORD_LENGTH) {
    return `Use at least ${MINIMUM_RECOVERY_PASSWORD_LENGTH} characters.`;
  }
  if (password !== confirmation) return 'Passwords do not match.';
  return null;
}
