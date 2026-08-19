// Authentication surface for the app.
//
// This module is deliberately the *only* place that talks to Supabase Auth, so
// adding a provider later (GitHub, Microsoft, ...) is a local change here.
// Email/password and Google are wired up now; each new provider is one more
// `signInWith*` helper.
//
// State is exposed as a Vue ref (`currentUser`) plus an `authReady` promise the
// router guard awaits, so route protection never races the initial session
// restore on a hard page load.
//
// The exported names are unchanged from the Firebase version this replaces, so
// the router, App shell and login screen did not have to learn a new vocabulary.

import { ref } from 'vue'

import { supabase } from './supabase'
import { ensureUserRecord } from './userProgress'

/** Reactive current user, or null when signed out. */
export const currentUser = ref(null)

/**
 * Resolves once the initial session restore has finished.
 *
 * `getSession()` is async - it reads persisted storage and may refresh an
 * expired token - so for the first moments after a page load the session is
 * null even for a signed-in user. A guard reading it directly would bounce
 * every hard refresh to /login and back a tick later. Awaiting this instead
 * means the guard never decides on an unresolved session.
 */
export const authReady = new Promise((resolve) => {
  supabase.auth
    .getSession()
    .then(({ data }) => {
      currentUser.value = data.session?.user ?? null
      resolve(currentUser.value)
    })
    .catch(() => {
      // A failed session read means "not signed in", not "hang forever".
      currentUser.value = null
      resolve(null)
    })
})

// Keep the ref in step with every later change: token refresh, sign-out in
// another tab, the OAuth redirect completing. Initialize or refresh the profile
// row for every sign-in regardless of provider, and never let that write hold
// up routing - it is bookkeeping, not authentication.
supabase.auth.onAuthStateChange((event, session) => {
  currentUser.value = session?.user ?? null
  if (session?.user && (event === 'SIGNED_IN' || event === 'INITIAL_SESSION')) {
    ensureUserRecord(session.user).catch((error) => {
      console.error('Failed to initialize user record:', error)
    })
  }
})

export function loginWithEmail(email, password) {
  return unwrap(supabase.auth.signInWithPassword({ email, password }))
}

export function registerWithEmail(email, password) {
  return unwrap(supabase.auth.signUp({ email, password }))
}

/**
 * Start the Google redirect flow.
 *
 * Unlike Firebase's signInWithPopup, this navigates the whole page away, so
 * nothing after the call in the caller will run. The post-login destination
 * therefore cannot be handled by the caller either - it has to survive the
 * round trip, which is what `redirectTo` is for. The app routes with
 * createWebHashHistory, so the target goes in the fragment.
 *
 * @param {string} [next] same-site path to land on, e.g. '/ide'
 */
export function loginWithGoogle(next = '/ide') {
  const base = `${window.location.origin}${window.location.pathname}`
  return unwrap(
    supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${base}#${next}` },
    }),
  )
}

export function sendPasswordReset(email) {
  return unwrap(
    supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}${window.location.pathname}#/login`,
    }),
  )
}

export function logout() {
  return unwrap(supabase.auth.signOut())
}

/**
 * supabase-js resolves with `{ data, error }` rather than rejecting, so a
 * caller that only try/catches would treat every failure as success. Convert
 * once, here, so every helper above throws like the Firebase calls they replace
 * and the login screen's existing error handling keeps working.
 */
async function unwrap(promise) {
  const { data, error } = await promise
  if (error) throw error
  return data
}
