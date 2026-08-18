// ==========================================================================
// Reads for the PROGRESS section and the recent-attempts log.
// ==========================================================================

import type { AttemptSummaryView, Db } from '@/lib/types/database';
import { applyAttemptFilter, COMPLETED, unwrap, type StatsFilter } from './core';

const SUMMARY = 'v_attempt_summary';

/**
 * Every completed attempt matching the filter, oldest first.
 *
 * ordered ascending by finished_at because this feeds the progress
 * multiline, and a time series that arrives newest-first has to be reversed by
 * every consumer. Sorting in Postgres costs nothing here and removes that
 * whole class of "why is my chart backwards" bug.
 */
export async function fetchAttemptSummaries(
  supabase: Db,
  userId: string,
  filter: StatsFilter = {},
): Promise<AttemptSummaryView[]> {
  const query = applyAttemptFilter(
    supabase.from(SUMMARY).select('*').eq('status', COMPLETED),
    userId,
    filter,
  ).order('finished_at', { ascending: true });

  return unwrap<AttemptSummaryView>('fetchAttemptSummaries', query);
}

/**
 * The most recent attempts, newest first, for the engagement section's log.
 *
 * deliberately NOT status-filtered. The log is the one place an abandoned
 * paper should still appear - "you started this and stopped" is exactly the
 * kind of thing a study log exists to show.
 */
export async function fetchRecentAttempts(
  supabase: Db,
  userId: string,
  limit = 20,
): Promise<AttemptSummaryView[]> {
  const query = supabase
    .from(SUMMARY)
    .select('*')
    .eq('user_id', userId)
    // started_at, not finished_at - an abandoned attempt has no finish.
    .order('started_at', { ascending: false })
    .limit(limit);

  return unwrap<AttemptSummaryView>('fetchRecentAttempts', query);
}

/** One attempt by id, or null. Used by the end screen's "review" path. */
export async function fetchAttemptById(
  supabase: Db,
  userId: string,
  attemptId: string,
): Promise<AttemptSummaryView | null> {
  const rows = await unwrap<AttemptSummaryView>(
    'fetchAttemptById',
    supabase.from(SUMMARY).select('*').eq('user_id', userId).eq('id', attemptId),
  );
  return rows[0] ?? null;
}

/**
 * The distinct values behind the three multiselects on the stats page.
 *
 * replaces the hardcoded ['Wade Cooper', …] / ['Apple','Banana','Cherry']
 * placeholders in StatsPage.vue. Derived from what the user has ACTUALLY sat,
 * so the filter bar can never offer a combination that yields nothing.
 */
export interface FilterOptions {
  subjectCodes: string[];
  subjectNames: Map<string, string>;
  examYears: number[];
  series: string[];
  variants: number[];
}

export async function fetchFilterOptions(
  supabase: Db,
  userId: string,
): Promise<FilterOptions> {
  const rows = await unwrap<
    Pick<AttemptSummaryView,
      'subject_code' | 'subject_name' | 'exam_year' | 'series' | 'variant'>
  >(
    'fetchFilterOptions',
    supabase
      .from(SUMMARY)
      .select('subject_code, subject_name, exam_year, series, variant')
      .eq('user_id', userId),
  );

  // distinct-ing in JS rather than SQL. Postgres has no cheap multi-column
  // DISTINCT through PostgREST, and this set is bounded by papers-sat, which is
  // in the hundreds at most - not worth a dedicated view.
  const subjectNames = new Map<string, string>();
  for (const r of rows) {
    if (r.subject_code) subjectNames.set(r.subject_code, r.subject_name ?? r.subject_code);
  }

  const uniqueSorted = <T>(values: (T | null)[]): T[] =>
    [...new Set(values.filter((v): v is T => v !== null && v !== undefined))]
      .sort((a, b) => (a > b ? 1 : a < b ? -1 : 0));

  return {
    subjectCodes: uniqueSorted(rows.map(r => r.subject_code)),
    subjectNames,
    examYears: uniqueSorted(rows.map(r => r.exam_year)),
    series: uniqueSorted(rows.map(r => r.series)),
    variants: uniqueSorted(rows.map(r => r.variant)),
  };
}
