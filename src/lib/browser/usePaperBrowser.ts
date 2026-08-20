// ==========================================================================
//
// The Paper Browser's data layer.
//
// Before this, BrowserPage.vue held a hardcoded array of 32 subject cards with
// hardcoded paper codes, a hardcoded "3 days ago" and a hardcoded
// "Recommended" tag, and none of the cards was clickable - the solver was only
// reachable from a sidebar link pinned to one paper. This composable replaces
// all of that with the catalogue (what CAN be sat) joined to exam_attempts
// (what HAS been sat).
//
// Mirrors lib/stats/useStats.ts deliberately: same auth handling, same
// loading/error shape, same "empty filter means no constraint" convention.
// ==========================================================================

import { computed, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { supabase, useAuthStore } from '@/stores/useAuth';
import { fetchPaperStates, type PaperAttemptState } from '@/lib/supabase/queries';
import {
  buildPaperEntries, condensedLabel, type PaperEntry,
} from '@/constants/paperCatalogue';
import {
  PaperProgress, defaultFilter, type BrowserFilter,
} from '@/components_browser/browserFilter';
import { EXAM_SERIES_LABEL } from '@/lib/types/enums';
import { AttemptStatus } from '@/lib/types/enums';

/** A paper plus everything the card needs to render it. */
export interface PaperCard extends PaperEntry {
  progress: PaperProgress;
  /** null when never attempted. */
  attempt: PaperAttemptState | null;
  /** '0620/s25/12' - the Cambridge shorthand shown in the card footer. */
  condensed: string;
  /** 'May/Jun 2025'. */
  sessionLabel: string;
  /** 'Never attempted' | '3 days ago'. */
  lastAttemptedLabel: string;
  /** Short, factual chips. Never more than three - the row scrolls otherwise. */
  tags: string[];
  /** Set when this paper is worth doing next, and why. */
  recommendation: string | null;
}

const DAY_MS = 86_400_000;

/**
 * relative time, not a date. The card is asking "is this stale?", and
 * "3 days ago" answers that where "2026-08-17" makes the reader do arithmetic.
 */
export function relativeTime(iso: string, now = Date.now()): string {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return 'unknown';
  const days = Math.floor((now - then) / DAY_MS);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`;
  const years = Math.floor(days / 365);
  return `${years} year${years === 1 ? '' : 's'} ago`;
}

function progressOf(state: PaperAttemptState | undefined): PaperProgress {
  if (!state) return PaperProgress.Unattempted;
  if (state.status === AttemptStatus.Completed) return PaperProgress.Completed;
  // An abandoned attempt is still "you started this" as far as the grid is
  // concerned - it is unfinished work, not a clean slate.
  return PaperProgress.InProgress;
}

/**
 * Which subjects to nudge the student towards.
 *
 * rule-based, and the rule is stated on the card. A subject qualifies when
 * they have completed at least two papers in it and averaged under 60% - low
 * enough to be worth more practice, and two papers is the least that makes an
 * average mean anything. Papers already sat are never recommended: the point
 * is to send them somewhere new.
 */
function weakSubjects(states: Map<string, PaperAttemptState>): Map<string, number> {
  const bySubject = new Map<string, { sum: number; n: number }>();
  for (const s of states.values()) {
    if (s.status !== AttemptStatus.Completed || s.accuracy === null) continue;
    const code = s.paperId.split('_')[0];
    const agg = bySubject.get(code) ?? { sum: 0, n: 0 };
    agg.sum += s.accuracy;
    agg.n += 1;
    bySubject.set(code, agg);
  }

  const weak = new Map<string, number>();
  for (const [code, { sum, n }] of bySubject) {
    const mean = sum / n;
    if (n >= 2 && mean < 0.6) weak.set(code, mean);
  }
  return weak;
}

export function usePaperBrowser() {
  const auth = useAuthStore();
  const { user } = storeToRefs(auth);

  const filter = reactive<BrowserFilter>(defaultFilter());
  const states = ref<Map<string, PaperAttemptState>>(new Map());
  const loading = ref(true);
  const error = ref<string | null>(null);

  async function load() {
    const userId = user.value?.id;
    if (!userId) {
      // Not an error - the guard means this is only the gap between mount and
      // session restore.
      states.value = new Map();
      loading.value = false;
      return;
    }
    loading.value = true;
    error.value = null;
    try {
      states.value = await fetchPaperStates(supabase, userId);
    } catch (e) {
      // The catalogue does not depend on the database, so the grid still works
      // with no attempt overlay. Say so rather than showing an empty page.
      error.value = e instanceof Error ? e.message : String(e);
      states.value = new Map();
    } finally {
      loading.value = false;
    }
  }

  // The attempt overlay is per-user and does not depend on the filter, so it is
  // fetched once per session rather than on every filter change - unlike the
  // stats page, whose filter is pushed down into SQL.
  watch(user, load, { immediate: true });

  /** Every paper the catalogue can offer, before the progress filter. */
  const entries = computed<PaperEntry[]>(() =>
    buildPaperEntries({
      subjectCodes: filter.subjectCodes,
      examYears: filter.examYears,
      series: filter.series,
      variants: filter.variants,
    }),
  );

  const cards = computed<PaperCard[]>(() => {
    const weak = weakSubjects(states.value);
    const now = Date.now();

    return entries.value.map((entry) => {
      const attempt = states.value.get(entry.id) ?? null;
      const progress = progressOf(attempt ?? undefined);
      const sessionLabel = `${EXAM_SERIES_LABEL[entry.series]} ${entry.examYear}`;

      const tags: string[] = [entry.qualification, sessionLabel];
      if (progress === PaperProgress.Completed && attempt?.accuracy !== null && attempt) {
        tags.push(`Scored ${Math.round(attempt.accuracy! * 100)}%`);
      } else if (progress === PaperProgress.InProgress) {
        tags.push('Unfinished');
      }

      const weakMean = weak.get(entry.code);
      const recommendation =
        progress === PaperProgress.Unattempted && weakMean !== undefined
          ? `You average ${Math.round(weakMean * 100)}% in ${entry.subject}`
          : null;

      return {
        ...entry,
        attempt,
        progress,
        condensed: condensedLabel(entry),
        sessionLabel,
        lastAttemptedLabel: attempt
          ? relativeTime(attempt.lastAttemptedAt, now)
          : 'Never attempted',
        tags,
        recommendation,
      };
    });
  });

  /**
   * The grid.
   *
   * Progress is filtered HERE rather than in buildPaperEntries because it is
   * not a property of the catalogue - it needs the attempt map, which the
   * catalogue knows nothing about.
   */
  const visibleCards = computed<PaperCard[]>(() => {
    if (!filter.progress.length) return cards.value;
    return cards.value.filter(c => filter.progress.includes(c.progress));
  });

  return { filter, cards, visibleCards, loading, error, reload: load };
}
