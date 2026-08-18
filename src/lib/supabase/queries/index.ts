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
} from './attempts';
export type { FilterOptions } from './attempts';

export { fetchDailyActivity, fetchHourOfDay, computeStreaks } from './activity';

export {
  fetchQuestionFlags,
  fetchCalibrationCurve,
  fetchScatterPoints,
  summariseFlags,
} from './focus';
export type { CalibrationPoint, FocusTotals, ScatterPoint } from './focus';

export { fetchSubjectStats, fetchTopicMastery } from './subjects';
export { fetchActiveGoals } from './goals';
