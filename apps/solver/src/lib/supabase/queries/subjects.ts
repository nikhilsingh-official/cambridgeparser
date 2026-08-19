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
 * returns [] until topics and paper_answers.topic_id are populated from
 * src/constants/topicMap.ts. That is content, not code - the caller should
 * HIDE the topic section on an empty result rather than render an empty radar,
 * which reads as broken. See STATS_PAGE_DESIGN.md §6.
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
