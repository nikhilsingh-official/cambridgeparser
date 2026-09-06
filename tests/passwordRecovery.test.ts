// ============================================================================
//
// Public state-rule tests for password recovery and mobile route access.
// ============================================================================

import assert from 'node:assert/strict';
import test from 'node:test';
import {
  parseRecoveryCallback,
  shouldClearRecoveryForAuthEvent,
  validateRecoveryPassword,
} from '../src/lib/auth/passwordRecovery.ts';
import { shouldBlockMobileLayout } from '../src/lib/layout/mobileAccess.ts';

test('callback parsing never treats URL tokens as recovery authorization', () => {
  assert.deepEqual(
    parseRecoveryCallback('', '#access_token=secret&refresh_token=secret&type=recovery'),
    { errorCode: null, errorDescription: null },
  );
});

test('recovery callback errors take precedence over recovery tokens', () => {
  assert.deepEqual(
    parseRecoveryCallback(
      '?error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid',
      '#access_token=secret&type=recovery',
    ),
    {
      errorCode: 'otp_expired',
      errorDescription: 'Email link is invalid',
    },
  );
});

test('a forged recovery type does not become application recovery state', () => {
  assert.deepEqual(
    parseRecoveryCallback('', '#type=recovery'),
    { errorCode: null, errorDescription: null },
  );
});

test('repeated sign-in preserves only the verified recovery session', () => {
  assert.equal(shouldClearRecoveryForAuthEvent('SIGNED_IN', 'recovery-token', 'recovery-token'), false);
  assert.equal(shouldClearRecoveryForAuthEvent('SIGNED_IN', 'recovery-token', 'ordinary-token'), true);
  assert.equal(shouldClearRecoveryForAuthEvent('SIGNED_OUT', 'recovery-token', null), true);
  assert.equal(shouldClearRecoveryForAuthEvent('TOKEN_REFRESHED', 'recovery-token', 'new-token'), false);
});

test('new password validation rejects short and mismatched values', () => {
  assert.equal(validateRecoveryPassword('short', 'short'), 'Use at least 8 characters.');
  assert.equal(validateRecoveryPassword('new-password', 'different'), 'Passwords do not match.');
  assert.equal(validateRecoveryPassword('12345678', '12345678'), null);
  assert.equal(validateRecoveryPassword('new-password', 'new-password'), null);
});

test('phone widths block app routes but keep public auth routes available', () => {
  assert.equal(shouldBlockMobileLayout(767, false), true);
  assert.equal(shouldBlockMobileLayout(768, false), false);
  assert.equal(shouldBlockMobileLayout(390, true), false);
});
