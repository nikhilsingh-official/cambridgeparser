// Realtime Database access for per-user progress.
//
// Schema (one subtree per authenticated user; rules restrict each user to their
// own subtree):
//
//   users/$uid/
//     profile/                identity + bookkeeping, written at first sign-in
//       email, displayName, createdAt, lastLoginAt, schemaVersion
//     progress/               one child per question record id
//       $recordId/
//         status              'not_started' | 'attempted' | 'solved'
//         bestScore, maxMarks
//         attempts            how many times submitted
//         lastSource          the most recent pseudocode submitted
//         updatedAt
//     stats/                  denormalised counters for cheap dashboard reads
//       attempted, solved
//
// The shape is intentionally shallow and keyed by id so it is cheap to extend
// (add fields under a record, add sibling trees like `bookmarks/` later).

import {
  ref as dbRef,
  get,
  set,
  update,
  runTransaction,
  onValue,
  serverTimestamp,
} from 'firebase/database'

import { db } from './firebase'

const SCHEMA_VERSION = 1

function userRef(uid, ...segments) {
  return dbRef(db, ['users', uid, ...segments].join('/'))
}

/**
 * Initialize a user's record on first sign-in; otherwise just stamp the login.
 * Idempotent and safe to call on every auth state change.
 * @param {import('firebase/auth').User} user
 */
export async function ensureUserRecord(user) {
  const profileRef = userRef(user.uid, 'profile')
  const snap = await get(profileRef)
  if (!snap.exists()) {
    await set(userRef(user.uid), {
      profile: {
        email: user.email || null,
        displayName: user.displayName || null,
        createdAt: serverTimestamp(),
        lastLoginAt: serverTimestamp(),
        schemaVersion: SCHEMA_VERSION,
      },
      // progress/ is created lazily as questions are attempted.
      stats: { attempted: 0, solved: 0 },
    })
  } else {
    await update(profileRef, { lastLoginAt: serverTimestamp() })
  }
}

/**
 * Record one grading attempt for a question, keeping the best score and moving
 * status forward (never backward, so a later low score doesn't un-solve it).
 * @param {string} uid
 * @param {string} recordId
 * @param {{score:number, maxMarks:number, source:string}} attempt
 */
export async function recordAttempt(uid, recordId, { score, maxMarks, source }) {
  const solved = maxMarks > 0 && score >= maxMarks
  const progressRef = userRef(uid, 'progress', recordId)
  await runTransaction(progressRef, (current) => {
    const prev = current || {}
    const wasSolved = prev.status === 'solved'
    return {
      status: solved || wasSolved ? 'solved' : 'attempted',
      bestScore: Math.max(prev.bestScore ?? 0, score),
      maxMarks,
      attempts: (prev.attempts ?? 0) + 1,
      lastSource: source ?? prev.lastSource ?? '',
      updatedAt: serverTimestamp(),
    }
  })
}

/**
 * Subscribe to a user's full progress map. Returns the unsubscribe function.
 * @param {string} uid
 * @param {(progress: Record<string, object>) => void} callback
 */
export function watchProgress(uid, callback) {
  return onValue(userRef(uid, 'progress'), (snap) => {
    callback(snap.val() || {})
  })
}
