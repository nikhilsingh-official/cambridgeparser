// ==========================================================================
//
// The per-question practice sequence. Feeds the metric model in
// src/lib/stats/model.ts, which is the only place that does anything with it.
//
// This is the one query on the page that returns a ROW PER QUESTION rather
// than a rollup, because three of the five metrics it powers cannot be
// computed from an aggregate - see the header of
// supabase/migrations/00000000000005_topic_practice.sql.
// ==========================================================================

import type { Db } from '@/lib/types/database';
import type { PracticeRow } from '@/lib/stats/model';
import { fetchCountedPages } from './pagination';

const PRACTICE_PAGE_SIZE = 10_000;

/**
 * Every answered, topic-tagged question the user has completed.
 *
 * ORDER MATTERS and is not left to PostgREST: knowledge tracing is a
 * recurrence over the sequence, and an unordered read would silently produce a
 * different mastery estimate on every page load. model.ts sorts defensively as
 * well, because "silently different" is the worst failure mode available.
 *
 * SIZE: one row per (question x topic). The model needs the whole sequence, so
 * this read is count-aware and paginated rather than silently accepting the
 * PostgREST response limit. With max_rows=10,000 current users take one request;
 * a lower hosted cap is detected through the exact count and read in batches.
 */
export async function fetchTopicPractice(
  supabase: Db,
  userId: string,
  subjectCodes?: string[],
): Promise<PracticeRow[]> {
  let query = supabase
    .from('v_topic_practice')
    .select('topic_id, topic_name, subject_code, is_correct, option_count, marks, local_date, started_at, paper_id, paper_number, question_number', { count: 'exact' })
    .eq('user_id', userId);

  if (subjectCodes?.length) query = query.in('subject_code', subjectCodes);

  // use stable tie-breakers as range pagination requires a deterministic
  // order even when several answers share the same attempt timestamp.
  query = query
    .order('started_at', { ascending: true })
    .order('paper_id', { ascending: true })
    .order('question_number', { ascending: true })
    .order('topic_id', { ascending: true });

  return fetchCountedPages<PracticeRow>(
    'fetchTopicPractice',
    PRACTICE_PAGE_SIZE,
    // exact count is what distinguishes a complete short result from a
    // response truncated by a server-side max_rows cap.
    (from, to) => query.range(from, to),
  );
}
