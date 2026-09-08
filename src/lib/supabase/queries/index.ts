// ==========================================================================
// Single entry point for the read layer, so components import from
// '@/lib/supabase/queries' rather than reaching into individual modules.
// ==========================================================================

export { unwrap, applyAttemptFilter, COMPLETED } from './core';
export type { StatsFilter, PostgrestResult, Filterable } from './core';

export {
  fetchAttemptSummaries,
  fetchRecentAttempts,
  fetchAttemptById,
  fetchFilterOptions,
  fetchPaperStates,
} from './attempts';
export type { FilterOptions, PaperAttemptState } from './attempts';

export { fetchDailyActivity, fetchHourOfDay, computeStreaks } from './activity';

export {
  fetchQuestionFlags,
  fetchScatterPoints,
  summariseFlags,
  fetchAnswerChanges,
} from './focus';
export type { FocusTotals, ScatterPoint, AnswerChangeSummary } from './focus';

export { fetchSubjectStats, fetchTopicMastery } from './subjects';
export { fetchTopicPractice } from './practice';
export { fetchPaperQuestionTopics } from './questionTopics';
export type { PaperQuestionTopic } from './questionTopics';
export { fetchPaperQuestionAnswers } from './paperQuestionAnswers';
export type { PaperQuestionAnswer } from './paperQuestionAnswers';
export { fetchActiveGoals } from './goals';

export {
  fetchIdeStats,
  fetchIdeDaily,
  fetchIdeAttempts,
  fetchIdeSubmissions,
  fetchIdeProgress,
} from './ide';
