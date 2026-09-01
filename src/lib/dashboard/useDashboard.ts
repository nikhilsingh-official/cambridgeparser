// ==========================================================================
//
// The dashboard's data layer.
//
// Before this, the dashboard was entirely literal: QuickView.vue had no
// <script> at all and displayed "10 days", "352", "12h 17m" and "157/170" as
// hardcoded text, and StatsPrev.vue rotated four invented figures. It was the
// landing page, so those were the first numbers anyone saw and none of them
// was about them.
//
// WHY NOT JUST CALL useStats(). It reads ten views to drive seven charts, a
// topic queue and a per-paper grade table. This page shows eight numbers and
// is the first thing that loads after sign-in, so it reads the two views that
// answer those eight and nothing else. The auth handling, the loading/error
// shape and the "watch the user id" pattern are deliberately identical to
// useStats.ts and usePaperBrowser.ts.
//
// It computes nothing. Every figure comes from lib/stats/model.ts or from the
// query helpers, so the dashboard and the stats page cannot disagree about
// what a streak or a trend is.
// ==========================================================================
import { computed, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { supabase, useAuthStore } from '@/stores/useAuth';
import {
  fetchAttemptSummaries, fetchDailyActivity, computeStreaks,
} from '@/lib/supabase/queries';
import type { AttemptSummaryView, DailyActivityView, IsoDate } from '@/lib/types/database';
import { accuracyTrend, recentActivity } from '@/lib/stats/model';
// "today" must use the user's calendar timezone, not UTC.
import { localIsoDate } from '@/lib/date/localIsoDate';

interface DashboardState {
  attempts: AttemptSummaryView[];
  daily: DailyActivityView[];
}

const EMPTY: DashboardState = { attempts: [], daily: [] };

export function useDashboard() {
  const auth = useAuthStore();
  const { user } = storeToRefs(auth);

  const state = reactive<DashboardState>({ ...EMPTY });
  const loading = ref(true);
  const error = ref<string | null>(null);

  async function load() {
    const userId = user.value?.id;
    if (!userId) {
      // Not an error - this is the moment between mount and session restore.
      Object.assign(state, EMPTY);
      loading.value = false;
      return;
    }
    loading.value = true;
    error.value = null;
    try {
      const [attempts, daily] = await Promise.all([
        fetchAttemptSummaries(supabase, userId),
        fetchDailyActivity(supabase, userId),
      ]);
      Object.assign(state, { attempts, daily });
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
      Object.assign(state, EMPTY);
    } finally {
      loading.value = false;
    }
  }

  watch(() => user.value?.id, load, { immediate: true });

  // ---------------------------------------------------------------- derived
  const hasData = computed(() => state.attempts.length > 0);

  // The streak is measured in the user's local dates, which is what
  // local_date stores - so "today" is passed in rather than read from the
  // clock inside the helper. Same reasoning as useStats.ts.
  const today = (): IsoDate => localIsoDate();

  const streaks = computed(() => computeStreaks(state.daily, today()));

  const totals = computed(() => {
    const marksAwarded = state.attempts.reduce((n, a) => n + (a.marks_awarded ?? 0), 0);
    const marksTotal = state.attempts.reduce((n, a) => n + (a.marks_total ?? 0), 0);
    return {
      papers: state.attempts.length,
      marksAwarded,
      marksTotal,
      timeMs: state.attempts.reduce((n, a) => n + (a.duration_ms ?? 0), 0),
    };
  });

  const recent = computed(() => recentActivity(state.attempts, today()));
  const trend = computed(() => accuracyTrend(state.attempts));

  return { state, loading, error, hasData, totals, streaks, recent, trend, reload: load };
}
