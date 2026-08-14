// Authentication surface for the app.
//
// This module is deliberately the *only* place that talks to Firebase Auth, so
// adding a provider later (GitHub, Microsoft, ...) is a local change here.
// Email/password and Google are wired up now; each new provider is one more
// `signInWith*` helper that ends by delegating to `ensureUserRecord`.
//
// State is exposed as a Vue ref (`currentUser`) plus an `authReady` promise the
// router guard awaits, so route protection never races the initial auth check
// on a hard page load.

import { ref } from 'vue'
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
} from 'firebase/auth'

import { auth } from './firebase'
import { ensureUserRecord } from './userProgress'

/** Reactive current user, or null when signed out. */
export const currentUser = ref(null)

/** Resolves once Firebase has reported the initial auth state (session restore). */
export const authReady = new Promise((resolve) => {
  let settled = false
  onAuthStateChanged(auth, async (user) => {
    currentUser.value = user
    // Routing depends only on Firebase Auth. Do not hold the initial route
    // hostage to a profile/database write that may be slow or unavailable.
    if (!settled) {
      settled = true
      resolve(user)
    }
    // Initialize/refresh the DB record for every sign-in regardless of provider
    // or whether it came from an interactive login or a restored session.
    if (user) {
      try {
        await ensureUserRecord(user)
      } catch (error) {
        console.error('Failed to initialize user record:', error)
      }
    }
  })
})

export function loginWithEmail(email, password) {
  return signInWithEmailAndPassword(auth, email, password)
}

export function registerWithEmail(email, password) {
  return createUserWithEmailAndPassword(auth, email, password)
}

export function loginWithGoogle() {
  return signInWithPopup(auth, new GoogleAuthProvider())
}

export function logout() {
  return signOut(auth)
}
