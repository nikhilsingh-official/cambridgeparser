import { defineStore } from 'pinia'
import { createClient } from '@supabase/supabase-js'
import { computed, ref } from 'vue'
import type { AuthError, Session, User } from '@supabase/supabase-js'
import type { Ref } from 'vue'
// recovery callback error parsing is token-blind and independently tested.
import {
  parseRecoveryCallback,
  shouldClearRecoveryForAuthEvent,
} from '@/lib/auth/passwordRecovery'

// was hardcoded to the local emulator. Moved to env with the emulator kept
// as the fallback so `npm run dev` still works with no .env present, but a
// deploy can point at the real project. Tracked in docs/future_work.md §5.
const SUPABASE_URL =
  import.meta.env.VITE_SUPABASE_URL ?? 'http://127.0.0.1:54321'
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ??
  'sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH'

// capture callback errors before supabase-js consumes and clears the
// implicit fragment during client initialization; URL text never grants access.
const initialRecoveryError = typeof window === 'undefined'
  ? { errorCode: null, errorDescription: null }
  : parseRecoveryCallback(window.location.search, window.location.hash)

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

export type EmailLoginOptions = { email: string; password: string; }
// expose only the OAuth providers offered by the login screen.
export type OAuthProvider = 'google' | 'azure' | 'github'
export type OAuthLoginOptions = { provider: OAuthProvider }
export type LoginOptions = EmailLoginOptions | OAuthLoginOptions;

/**
 * resolves once the initial session restore has finished.
 *
 * This is the whole reason route guards can work. `supabase.auth.getSession()`
 * is async (it reads persisted storage and may refresh an expired token), so
 * for the first moments after a page load `session` is null even for a signed-in
 * user. A guard that reads it directly would bounce every hard refresh to
 * /login, then bounce back a tick later - the classic auth-flash.
 *
 * The guard awaits this instead, so it never decides on an unresolved session.
 * It is module-level rather than store state because the guard needs it before
 * any component has mounted.
 */
let resolveAuthReady: () => void
export const authReady: Promise<void> = new Promise((resolve) => {
  resolveAuthReady = resolve
})

export const useAuthStore = defineStore("auth", () => {
  const session: Ref<Session | null> = ref(null);

  // was `const jwt = session.value?.access_token` evaluated ONCE at store
  // creation, when session is always null - so it was permanently undefined.
  // A computed tracks the session and survives token refresh.
  const jwt = computed<string | null>(() => session.value?.access_token ?? null);
  const user = computed<User | null>(() => session.value?.user ?? null);
  const isAuthenticated = computed<boolean>(() => session.value !== null);
  // recovery authorization is narrower than ordinary authentication. A
  // persisted normal session must never unlock the new-password form.
  const passwordRecovery = ref(false);
  const passwordRecoveryError = ref<string | null>(
    initialRecoveryError.errorCode ?? initialRecoveryError.errorDescription,
  );
  // bind recovery authorization to the exact Supabase-verified session,
  // not to attacker-controlled callback parameters or an unrelated login.
  let recoveryAccessToken: string | null = null;

  let initialised = false;

  async function init() {
    // App.vue calls init() on every setup; guard against double-subscribing
    // to onAuthStateChange, which would otherwise stack listeners on HMR.
    if (initialised) return;
    initialised = true;

    // the listener is registered BEFORE the await. Registering it after
    // leaves a window in which a token refresh completing mid-await is missed.
    supabase.auth.onAuthStateChange((event, newSession) => {
      session.value = newSession;
      // Supabase emits this instead of SIGNED_IN for a valid recovery link.
      if (event === 'PASSWORD_RECOVERY' && newSession) {
        passwordRecovery.value = true;
        passwordRecoveryError.value = null;
        recoveryAccessToken = newSession.access_token;
      } else if (event === 'TOKEN_REFRESHED' && passwordRecovery.value && newSession) {
        recoveryAccessToken = newSession.access_token;
      } else if (shouldClearRecoveryForAuthEvent(
        event,
        recoveryAccessToken,
        newSession?.access_token ?? null,
      )) {
        clearPasswordRecovery();
      }
    });

    try {
      const { data } = await supabase.auth.getSession();
      session.value = data.session;
    } finally {
      // resolved even on failure. A network error must not hang every route
      // guard forever - it should fall through to "not signed in".
      resolveAuthReady();
    }
  }

  /**
   * no longer calls router.push(). Redirecting from inside the store meant
   * every caller landed on "/" regardless of where they were headed, which is
   * what made the "return to the page you wanted" behaviour impossible. The
   * caller now decides.
   */
  async function login(choice: LoginOptions, redirectPath = '/') {
    if ("email" in choice) {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: choice.email,
        password: choice.password,
      });
      if (error) throw error;
      session.value = data.session;
      return data;
    }

    // BUG FIX. This built `${location.origin}/${redirect}` from a caller
    // that passed "dashboard", producing /dashboard - which is not a route in
    // this app (the dashboard is at "/"), so every OAuth sign-in returned to a
    // blank unmatched route. redirectPath is now a real path, used as given.
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: choice.provider,
      options: { redirectTo: `${location.origin}${redirectPath}` },
    });
    if (error) throw error;
    return data;
  }

  /**
   * new. There was no way to create an account from the app at all -
   * the only user existed because it had been made by hand.
   *
   * Returns whether Supabase requires email confirmation: when confirmation is
   * on, signUp resolves with a user but NO session, and the UI has to say
   * "check your email" rather than silently appearing to do nothing.
   */
  async function signUp(email: string, password: string) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${location.origin}/login` },
    });
    if (error) throw error;

    session.value = data.session;
    return { needsConfirmation: data.session === null, user: data.user };
  }

  /** new - the "forgot password" path had no implementation. */
  async function sendPasswordReset(email: string) {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${location.origin}/reset-password`,
    });
    if (error) throw error;
  }

  /** update only inside a recovery session, then discard that session. */
  async function updateRecoveredPassword(password: string) {
    if (!passwordRecovery.value || !session.value
        || session.value.access_token !== recoveryAccessToken) {
      throw new Error('This password reset link is invalid or has expired.');
    }
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw error;
    passwordRecovery.value = false;
    passwordRecoveryError.value = null;
    await logout();
  }

  /** clear transient recovery state before requesting a replacement link. */
  function clearPasswordRecovery() {
    passwordRecovery.value = false;
    passwordRecoveryError.value = null;
    recoveryAccessToken = null;
  }

  async function logout() {
    // local scope ends only this browser's session. Verify storage is
    // actually empty before callers navigate away, even if remote revocation
    // returned an error after auth-js removed the local session.
    let signOutError: unknown = null;
    try {
      ({ error: signOutError } = await supabase.auth.signOut({ scope: 'local' }));
    } catch (error) {
      signOutError = error;
    }
    clearPasswordRecovery();
    const { data, error: sessionError } = await supabase.auth.getSession();
    if (sessionError) throw sessionError;
    session.value = data.session;
    if (data.session) {
      throw signOutError ?? new Error('The local session could not be cleared.');
    }
  }

  return {
    session, jwt, user, isAuthenticated, passwordRecovery, passwordRecoveryError,
    init, login, signUp, sendPasswordReset, updateRecoveredPassword,
    clearPasswordRecovery, logout,
  }
})

/**
 * Supabase throws AuthError, not Error, and its messages are lowercase
 * server strings ("Invalid login credentials"). Mapped to something a person
 * can act on - an unmapped message is passed through rather than swallowed.
 */
export function authErrorMessage(err: unknown): string {
  // Auth error codes are Supabase's stable contract; message matching is
  // retained only as a fallback for network errors and older/local responses.
  const code = (err as AuthError | null)?.code;
  const raw = (err as AuthError | Error | null)?.message ?? String(err);

  if (code === 'weak_password') return 'Choose a stronger password.';
  if (code === 'same_password') return 'Choose a password you have not used already.';
  if (code === 'validation_failed') return 'Check that your password meets the password requirements.';
  if (code === 'session_expired' || code === 'session_not_found'
      || code === 'otp_expired' || code === 'bad_jwt') {
    return 'This password reset link is invalid or has expired.';
  }
  if (code === 'over_email_send_rate_limit' || code === 'over_request_rate_limit') {
    return 'Too many attempts. Wait a moment and try again.';
  }
  if (/invalid login credentials/i.test(raw)) return 'That email and password do not match.';
  if (/email not confirmed/i.test(raw))       return 'Check your inbox and confirm your email first.';
  if (/user already registered/i.test(raw))   return 'An account with that email already exists.';
  if (/password should be at least/i.test(raw)) return 'Password must be at least 6 characters.';
  if (/weak_password|weak password/i.test(raw)) return 'Choose a stronger password.';
  if (/same_password|same password/i.test(raw)) return 'Choose a password you have not used already.';
  if (/session_expired|session_not_found|invalid.*token|expired/i.test(raw))
    return 'This password reset link is invalid or has expired.';
  if (/rate limit|too many/i.test(raw))       return 'Too many attempts. Wait a moment and try again.';
  if (/failed to fetch|networkerror/i.test(raw))
    return 'Cannot reach the server. Is Supabase running?';
  return raw;
}
