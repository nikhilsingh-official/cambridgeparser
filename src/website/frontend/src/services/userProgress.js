// Per-user profile and question progress, in Postgres.
//
// Replaces the Firebase Realtime Database subtree that used to live at
// users/$uid/. The shape is the same information, normalised:
//
//   ide_profiles   one row per user   email, display_name, created_at, last_login_at
//   ide_progress   one row per (user, question record)
//                  status ('not_started' | 'attempted' | 'solved'),
//                  best_score, max_marks, attempts, last_source, updated_at
//   v_ide_stats    the {attempted, solved} counters, as a view
//
// Two things moved server-side in the process, both because they are integrity
// rules and integrity rules in the client are advisory:
//
//   - "keep the best score, never un-solve a solved question" was a client-side
//     runTransaction; it is now record_ide_attempt() in the database.
//   - the stats counters were denormalised because RTDB cannot aggregate.
//     Postgres can, so they are a view and cannot drift from the rows.
//
// Every table here has RLS enabled and policies keyed on auth.uid(), so these
// calls need no user id passed in - the database derives it from the caller's
// token and will not return anyone else's rows.

import { supabase } from './supabase'

/**
 * Initialize a user's profile row on first sign-in; otherwise stamp the login.
 * Idempotent and safe to call on every auth state change.
 * @param {import('@supabase/supabase-js').User} user
 */
export async function ensureUserRecord(user) {
  const { error } = await supabase
    .from('ide_profiles')
    .upsert(
      {
        user_id: user.id,
        email: user.email ?? null,
        // Google returns a name in user_metadata; email/password sign-ups have
        // none, and null is the honest answer rather than a guess from the
        // local part of the address.
        display_name:
          user.user_metadata?.full_name ?? user.user_metadata?.name ?? null,
        last_login_at: new Date().toISOString(),
      },
      { onConflict: 'user_id' },
    )
  // created_at keeps its default on first insert and is left alone afterwards,
  // so the upsert cannot rewrite a user's join date.
  if (error) throw error
}

/**
 * Record one grading attempt for a question.
 * @param {string} recordId
 * @param {{score:number, maxMarks:number, source:string}} attempt
 * @returns {Promise<object>} the updated progress row
 */
export async function recordAttempt(recordId, { score, maxMarks, source }) {
  const { data, error } = await supabase.rpc('record_ide_attempt', {
    p_record_id: String(recordId),
    p_score: score,
    p_max_marks: maxMarks,
    p_source: source ?? null,
  })
  if (error) throw error
  return data
}

/**
 * Read a user's full progress map, keyed by record id to match how the IDE
 * looks progress up.
 * @returns {Promise<Record<string, object>>}
 */
export async function fetchProgress() {
  const { data, error } = await supabase.from('ide_progress').select('*')
  if (error) throw error
  return Object.fromEntries((data ?? []).map((row) => [row.record_id, row]))
}

/**
 * Subscribe to a user's progress. Returns the unsubscribe function, matching
 * the RTDB `onValue` contract this replaces.
 *
 * Postgres changes are not streamed unless the table is added to the
 * `supabase_realtime` publication, which it is not. So this fetches once and
 * then refetches on each change it is told about, which is what the IDE needs -
 * progress only changes in response to this tab's own submissions.
 */
export function watchProgress(callback) {
  let active = true
  const refresh = () => {
    fetchProgress()
      .then((progress) => { if (active) callback(progress) })
      .catch((error) => console.error('Failed to read progress:', error))
  }
  refresh()
  const channel = supabase
    .channel('ide_progress_changes')
    .on('postgres_changes',
        { event: '*', schema: 'public', table: 'ide_progress' },
        refresh)
    .subscribe()
  return () => {
    active = false
    supabase.removeChannel(channel)
  }
}
