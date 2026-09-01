// ==========================================================================
//
// Reads for the pseudocode IDE's side of the stats.
//
// These are the first consumers v_ide_stats has ever had: it was created in
// 00000000000001_ide_schema.sql and, per docs/roadmap.md A4, read an empty
// table and returned 0 rows to nobody. What made it empty was that nothing
// called record_ide_attempt(); that is now written by the grade Edge Function,
// so these have something to read.
//
// NOTHING IS WRITTEN HERE. The IDE's only write goes through the grading
// endpoint, deliberately - a score the browser could send is a score the
// browser could invent (docs/roadmap.md B4). This module is read-only, and
// there is no write helper to reach for.
// ==========================================================================

import type {
  Db, IdeAttemptRow, IdeDailyView, IdeProgressRow, IdeStatsView, IsoDate,
} from '@/lib/types/database';
import { unwrap } from './core';

/**
 * The one-row summary: attempted, solved, submissions, marks, last activity.
 *
 * Returns null rather than a zeroed row for a student who has never submitted.
 * The view has no row for them at all, and a fabricated `{ solved: 0 }` reads
 * in the UI as a measurement rather than as an absence - the same distinction
 * QuickView.vue draws with an em dash.
 */
export async function fetchIdeStats(
  supabase: Db,
  userId: string,
): Promise<IdeStatsView | null> {
  const rows = await unwrap<IdeStatsView>(
    'fetchIdeStats',
    supabase.from('v_ide_stats').select('*').eq('user_id', userId),
  );
  return rows[0] ?? null;
}

/**
 * Per-day IDE totals, the sibling of fetchDailyActivity.
 *
 * Same shape and the same `local_date` key, so a caller can merge the two into
 * one streak or one heatmap without either side knowing about the other.
 */
export async function fetchIdeDaily(
  supabase: Db,
  userId: string,
  from?: IsoDate,
  to?: IsoDate,
): Promise<IdeDailyView[]> {
  let query = supabase.from('v_ide_daily').select('*').eq('user_id', userId);
  if (from) query = query.gte('local_date', from);
  if (to)   query = query.lte('local_date', to);
  return unwrap<IdeDailyView>(
    'fetchIdeDaily',
    query.order('local_date', { ascending: true }),
  );
}

/**
 * The append-only submission log, oldest first.
 *
 * `source` is excluded: it is the largest column by far and no caller that
 * wants a trend line wants twenty thousand characters of pseudocode per point.
 * fetchIdeSubmissions() below fetches it for the one question that needs it.
 */
export async function fetchIdeAttempts(
  supabase: Db,
  userId: string,
  limit = 500,
): Promise<Omit<IdeAttemptRow, 'source'>[]> {
  return unwrap<Omit<IdeAttemptRow, 'source'>>(
    'fetchIdeAttempts',
    supabase
      .from('ide_attempts')
      .select('id, user_id, record_id, score, max_marks, answer_kind, points, local_date, client_timezone, created_at')
      .eq('user_id', userId)
      .order('created_at', { ascending: true })
      .limit(limit),
  );
}

/** Every submission for one question, newest first - the per-question history. */
export async function fetchIdeSubmissions(
  supabase: Db,
  userId: string,
  recordId: string,
): Promise<IdeAttemptRow[]> {
  return unwrap<IdeAttemptRow>(
    'fetchIdeSubmissions',
    supabase
      .from('ide_attempts')
      .select('*')
      .eq('user_id', userId)
      .eq('record_id', recordId)
      .order('created_at', { ascending: false }),
  );
}

/**
 * Per-question status, for the problem explorer's badges.
 *
 * Returned as a Map keyed by record id because that is how the explorer uses
 * it - one lookup per rendered row, against a list that can run to hundreds of
 * questions.
 */
export async function fetchIdeProgress(
  supabase: Db,
  userId: string,
): Promise<Map<string, IdeProgressRow>> {
  const rows = await unwrap<IdeProgressRow>(
    'fetchIdeProgress',
    supabase.from('ide_progress').select('*').eq('user_id', userId),
  );
  return new Map(rows.map(row => [String(row.record_id), row]));
}
