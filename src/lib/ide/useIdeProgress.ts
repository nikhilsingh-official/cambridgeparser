// ==========================================================================
//
// The IDE's read of its own progress: which questions are solved, and the
// one-row summary behind them.
//
// It does not write. The submission is recorded by the grade Edge Function,
// from the server that graded it, so the only thing the browser can do afterwards is
// ask what the database now says - which is what refresh() is for. That is a
// deliberately weaker capability than the client used to have under Firebase,
// where the browser wrote its own score.
//
// The auth handling and the "watch the user id" pattern are the same as
// lib/dashboard/useDashboard.ts and lib/stats/useStats.ts.
// ==========================================================================
import { computed, ref, shallowRef, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { supabase, useAuthStore } from '@/stores/useAuth';
import { fetchIdeProgress, fetchIdeStats } from '@/lib/supabase/queries';
import type { IdeProgressRow, IdeStatsView } from '@/lib/types/database';

export function useIdeProgress() {
  const auth = useAuthStore();
  const { user } = storeToRefs(auth);

  // shallowRef: the Map is replaced wholesale on every load and is read once
  // per rendered row in a list that runs to hundreds of questions. Deep
  // reactivity over it would buy nothing and cost on every render.
  const progress = shallowRef<Map<string, IdeProgressRow>>(new Map());
  const stats = ref<IdeStatsView | null>(null);
  const loading = ref(true);
  const error = ref<string | null>(null);

  async function load() {
    const userId = user.value?.id;
    if (!userId) {
      // Not an error - the IDE is usable signed out, it just cannot grade, so
      // there is no progress to show rather than a failure to report.
      progress.value = new Map();
      stats.value = null;
      loading.value = false;
      return;
    }
    loading.value = true;
    error.value = null;
    try {
      const [rows, summary] = await Promise.all([
        fetchIdeProgress(supabase, userId),
        fetchIdeStats(supabase, userId),
      ]);
      progress.value = rows;
      stats.value = summary;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
      progress.value = new Map();
      stats.value = null;
    } finally {
      loading.value = false;
    }
  }

  watch(() => user.value?.id, load, { immediate: true });

  /** Questions with at least one submission, and of those, the solved ones. */
  const solved = computed(() => stats.value?.solved ?? 0);
  const attempted = computed(() => stats.value?.attempted ?? 0);

  function statusOf(recordId: string | number): 'solved' | 'attempted' | null {
    const row = progress.value.get(String(recordId));
    if (!row || row.status === 'not_started') return null;
    return row.status;
  }

  return { progress, stats, loading, error, solved, attempted, statusOf, refresh: load };
}
