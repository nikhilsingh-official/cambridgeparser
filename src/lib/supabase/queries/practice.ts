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
import { unwrap } from './core';

/**
 * Every answered, topic-tagged question the user has completed.
 *
 * ORDER MATTERS and is not left to PostgREST: knowledge tracing is a
 * recurrence over the sequence, and an unordered read would silently produce a
 * different mastery estimate on every page load. model.ts sorts defensively as
 * well, because "silently different" is the worst failure mode available.
 *
 * SIZE: one row per (question x topic). A student who has sat 50 papers of 40
 * questions with 1.2 topics each is ~2,400 rows - fine for one read, but this
 * is the query to watch if a user ever gets into the thousands of papers. The
 * fix then is a materialised per-topic summary, not pagination: the model
 * needs the whole sequence or none of it.
 */
export async function fetchTopicPractice(
  supabase: Db,
  userId: string,
  subjectCodes?: string[],
): Promise<PracticeRow[]> {
  let query = supabase
    .from('v_topic_practice')
    .select('topic_id, topic_name, subject_code, is_correct, option_count, marks, local_date, started_at, paper_id, paper_number, question_number')
    .eq('user_id', userId);

  if (subjectCodes?.length) query = query.in('subject_code', subjectCodes);

  return unwrap<PracticeRow>(
    'fetchTopicPractice',
    query.order('started_at', { ascending: true }),
  );
}
