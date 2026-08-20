// ==========================================================================
//
// The stats page's data layer: one composable that owns every read, so the
// page's components stay presentational and the filter has exactly one place
// to invalidate.
//
// The query layer under lib/supabase/queries/ was built in `aec4e13` and had
// never been called by anything. This is its first consumer.
//
// Loading is all-at-once rather than per-panel: the panels share a filter, and
// staggered per-panel spinners on a page this dense reads as a page that is
// broken rather than a page that is loading.
// ==========================================================================
import { computed, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { supabase, useAuthStore } from '@/stores/useAuth';
import {
  fetchAttemptSummaries,
  fetchDailyActivity,
  fetchHourOfDay,
  fetchSubjectStats,
  fetchQuestionFlags,
  fetchCalibrationCurve,
  fetchFilterOptions,
  computeStreaks,
  summariseFlags,
  type StatsFilter,
  type FilterOptions,
  type CalibrationPoint,
  type FocusTotals,
} from '@/lib/supabase/queries';
import type {
  AttemptSummaryView, DailyActivityView, HourOfDayView,
  SubjectStatsView, QuestionFlagsView, IsoDate,
} from '@/lib/types/database';

export interface StatsState {
  attempts: AttemptSummaryView[];
  daily: DailyActivityView[];
  hours: HourOfDayView[];
  subjects: SubjectStatsView[];
  flags: QuestionFlagsView[];
  calibration: CalibrationPoint[];
  options: FilterOptions | null;
}

const EMPTY: StatsState = {
  attempts: [], daily: [], hours: [], subjects: [], flags: [], calibration: [], options: null,
};

export function useStats() {
  const auth = useAuthStore();
  const { user } = storeToRefs(auth);

  const filter = reactive<StatsFilter>({});
  const state = reactive<StatsState>({ ...EMPTY });
  const loading = ref(true);
  const error = ref<string | null>(null);

  async function load() {
    const userId = user.value?.id;
    if (!userId) {
      // Not an error: the router guard means this only happens in the moment
      // between mount and session restore.
      Object.assign(state, EMPTY);
      loading.value = false;
      return;
    }
    loading.value = true;
    error.value = null;
    try {
      // Parallel, not sequential: seven independent reads chained with await
      // would take seven round trips for no reason.
      const [attempts, daily, hours, subjects, flags, calibration, options] = await Promise.all([
        fetchAttemptSummaries(supabase, userId, filter),
        // Not every view carries the full filter. v_daily_activity is keyed
        // on date only, and v_subject_stats / v_hour_of_day / the calibration
        // buckets aggregate across papers - so they take what they support and
        // the rest of the filter is applied to the attempt list. Passing an
        // unsupported filter silently to a query that ignores it would be
        // worse: the page would look filtered when it was not.
        fetchDailyActivity(supabase, userId, filter.from, filter.to),
        fetchHourOfDay(supabase, userId),
        fetchSubjectStats(supabase, userId),
        fetchQuestionFlags(supabase, userId, filter),
        fetchCalibrationCurve(supabase, userId),
        // Filter options describe what COULD be selected, so they are read
        // unfiltered - otherwise selecting Chemistry removes every other
        // subject from the dropdown and the filter becomes a one-way door.
        fetchFilterOptions(supabase, userId),
      ]);
      Object.assign(state, { attempts, daily, hours, subjects, flags, calibration, options });
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
      Object.assign(state, EMPTY);
    } finally {
      loading.value = false;
    }
  }

  watch(() => user.value?.id, load, { immediate: true });
  watch(filter, load, { deep: true });

  // ---------------------------------------------------------------- derived
  const hasData = computed(() => state.attempts.length > 0);

  const totals = computed(() => {
    const marksAwarded = state.attempts.reduce((n, a) => n + (a.marks_awarded ?? 0), 0);
    const marksTotal = state.attempts.reduce((n, a) => n + (a.marks_total ?? 0), 0);
    const timeMs = state.attempts.reduce((n, a) => n + (a.duration_ms ?? 0), 0);
    const questions = state.attempts.reduce((n, a) => n + (a.questions_recorded ?? 0), 0);
    return {
      papers: state.attempts.length,
      questions,
      marksAwarded,
      marksTotal,
      // Accuracy is marks/total, not a self-reported score - the definition
      // settled in docs/stats_page_design.md §0.1. Guard the divide: an empty
      // filter selection must render "-", never NaN%.
      accuracy: marksTotal > 0 ? marksAwarded / marksTotal : null,
      timeMs,
      avgPaperMs: state.attempts.length > 0 ? timeMs / state.attempts.length : null,
    };
  });

  // computeStreaks needs "today" passed in rather than reading the clock: the
  // streak is measured in the user's local dates, which is what local_date
  // stores, and new Date() inside the helper would use the machine's.
  const today = () => new Date().toISOString().slice(0, 10) as IsoDate;
  const streaks = computed(() => computeStreaks(state.daily, today()));
  const focus = computed<FocusTotals>(() => summariseFlags(state.flags));

  return { filter, state, loading, error, hasData, totals, streaks, focus, reload: load };
}
