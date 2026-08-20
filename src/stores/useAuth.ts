import { defineStore } from 'pinia'
import { createClient } from '@supabase/supabase-js'
import { computed, ref } from 'vue'
import type { AuthError, Session, User } from '@supabase/supabase-js'
import type { Ref } from 'vue'

// was hardcoded to the local emulator. Moved to env with the emulator kept
// as the fallback so `npm run dev` still works with no .env present, but a
// deploy can point at the real project. Tracked in docs/future_work.md §5.
const SUPABASE_URL =
  import.meta.env.VITE_SUPABASE_URL ?? 'http://127.0.0.1:54321'
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ??
  'sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH'

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

export type EmailLoginOptions = { email: string; password: string; }
export type OAuthProvider = 'google' | 'azure' | 'twitter'
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

  let initialised = false;

  async function init() {
    // App.vue calls init() on every setup; guard against double-subscribing
    // to onAuthStateChange, which would otherwise stack listeners on HMR.
    if (initialised) return;
    initialised = true;

    // the listener is registered BEFORE the await. Registering it after
    // leaves a window in which a token refresh completing mid-await is missed.
    supabase.auth.onAuthStateChange((_event, newSession) => {
      session.value = newSession;
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
      redirectTo: `${location.origin}/login`,
    });
    if (error) throw error;
  }

  async function logout() {
    await supabase.auth.signOut()
    session.value = null
  }

  return {
    session, jwt, user, isAuthenticated,
    init, login, signUp, sendPasswordReset, logout,
  }
})

/**
 * Supabase throws AuthError, not Error, and its messages are lowercase
 * server strings ("Invalid login credentials"). Mapped to something a person
 * can act on - an unmapped message is passed through rather than swallowed.
 */
export function authErrorMessage(err: unknown): string {
  const raw = (err as AuthError | Error | null)?.message ?? String(err);

  if (/invalid login credentials/i.test(raw)) return 'That email and password do not match.';
  if (/email not confirmed/i.test(raw))       return 'Check your inbox and confirm your email first.';
  if (/user already registered/i.test(raw))   return 'An account with that email already exists.';
  if (/password should be at least/i.test(raw)) return 'Password must be at least 6 characters.';
  if (/rate limit|too many/i.test(raw))       return 'Too many attempts. Wait a moment and try again.';
  if (/failed to fetch|networkerror/i.test(raw))
    return 'Cannot reach the server. Is Supabase running?';
  return raw;
}
