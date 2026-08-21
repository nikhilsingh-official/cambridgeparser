// ==========================================================================
// Subject-level rollups and topic mastery.
// ==========================================================================

import type { Db, SubjectStatsView, TopicMasteryView } from '@/lib/types/database';
import { unwrap } from './core';

/** Per-subject rollup - the header sunburst and the strongest/weakest cards. */
export async function fetchSubjectStats(
  supabase: Db,
  userId: string,
): Promise<SubjectStatsView[]> {
  return unwrap<SubjectStatsView>(
    'fetchSubjectStats',
    supabase
      .from('v_subject_stats')
      .select('*')
      .eq('user_id', userId)
      .order('attempts', { ascending: false }),
  );
}

/**
 * Per-topic mastery.
 *
 * returns [] for any paper outside the tagged set - supabase/seeds/03_topics.sql
 * covers the multiple-choice syllabuses only, and 82% of the browsable years
 * within them. The caller should HIDE the topic section on an empty result
 * rather than render an empty radar, which reads as broken. See
 * docs/stats_page_design.md §6.
 *
 * A question can carry more than one topic, so marks_total summed across
 * topics can exceed the paper's marks. Read it per topic; v_subject_stats is
 * what answers "how am I doing at Physics".
 */
export async function fetchTopicMastery(
  supabase: Db,
  userId: string,
  subjectCode?: string,
): Promise<TopicMasteryView[]> {
  let query = supabase.from('v_topic_mastery').select('*').eq('user_id', userId);
  if (subjectCode) query = query.eq('subject_code', subjectCode);

  return unwrap<TopicMasteryView>(
    'fetchTopicMastery',
    query.order('accuracy', { ascending: true }),
  );
}
