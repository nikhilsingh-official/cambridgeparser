// Central Firebase initialization for the web client.
//
// The values below are the Firebase *web* config: a set of public identifiers
// that are meant to ship in the client bundle. They do not grant access on
// their own -- access is enforced by Firebase Security Rules (see
// database.rules.json) and Authentication. The only true secret in this project
// (the OpenRouter API key) lives exclusively in the Cloud Function via Secret
// Manager and is never imported here.
//
// Everything Firebase-related is created once, here, and imported elsewhere, so
// the rest of the app never touches the SDK's init surface directly.

import { initializeApp } from 'firebase/app'
import { getAuth, connectAuthEmulator } from 'firebase/auth'
import { getDatabase, connectDatabaseEmulator } from 'firebase/database'
import { getAnalytics, isSupported as analyticsIsSupported } from 'firebase/analytics'

const firebaseConfig = {
  apiKey: 'AIzaSyAur3mTM0xxxFj5GSvLm3RCisbjmkYLroU',
  authDomain: 'pseudocode-parser.firebaseapp.com',
  // Realtime Database URL is NOT part of the console's copy-paste snippet; it is
  // shown when you create the database. This instance is in Singapore
  // (asia-southeast1). Override via VITE_FIREBASE_DATABASE_URL if it ever moves.
  databaseURL:
    import.meta.env.VITE_FIREBASE_DATABASE_URL
    || 'https://pseudocode-parser-default-rtdb.asia-southeast1.firebasedatabase.app',
  projectId: 'pseudocode-parser',
  storageBucket: 'pseudocode-parser.firebasestorage.app',
  messagingSenderId: '355403012189',
  appId: '1:355403012189:web:cd7b26586404590e0d15b4',
  measurementId: 'G-BBTZX3Z8M0',
}

export const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const db = getDatabase(app)

// Point Auth + RTDB at the local Firebase Emulator Suite when
// VITE_USE_FIREBASE_EMULATORS=true (set by the emulator npm scripts). This keeps
// local testing entirely off the real project — no live users, no live data.
// Grading (/api/grade) is handled separately: the Vite dev plugin in dev, or the
// functions emulator when serving the built app through the hosting emulator.
if (import.meta.env.VITE_USE_FIREBASE_EMULATORS === 'true') {
  connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true })
  connectDatabaseEmulator(db, '127.0.0.1', 9000)
}

// Analytics only works in a browser with a supported environment, and it is not
// essential to the app, so initialize it opportunistically and never let a
// failure here break startup.
export let analytics = null
analyticsIsSupported()
  .then((supported) => {
    if (supported) analytics = getAnalytics(app)
  })
  .catch(() => {
    /* analytics unavailable (e.g. blocked or unsupported) -- ignore */
  })
