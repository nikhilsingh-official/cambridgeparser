<script setup lang="ts">
// ==========================================================================
//
// The headline card strip, now computed from real attempts.
//
// Was a `testStats` array of 30 cards with Math.random() metrics - which meant
// the strip changed on every re-render and could never be checked against
// anything. Cards are now derived, and a card whose input is missing is
// DROPPED rather than rendered with a placeholder: a strip of honest four
// cards beats a strip of seventeen where thirteen say "—".
// ==========================================================================
import { computed } from 'vue';
import { StatCategory } from '@/lib/types/enums';
import StatsCard from './StatsCard.vue';
import { pct, duration, count } from '@/lib/stats/format';
import type { AttemptSummaryView, SubjectStatsView } from '@/lib/types/database';

const props = defineProps<{
  attempts: AttemptSummaryView[];
  subjects: SubjectStatsView[];
  streaks: { current: number; longest: number };
  totals: {
    papers: number; questions: number; marksAwarded: number; marksTotal: number;
    accuracy: number | null; timeMs: number; avgPaperMs: number | null;
  };
  bottom?: boolean;
}>();

interface Card { category: StatCategory; text: string; metricData: string }

const cards = computed<Card[]>(() => {
  const out: Card[] = [];
  const push = (category: StatCategory, text: string | null, metric: string | null) => {
    if (text === null || metric === null) return;
    out.push({ category, text, metricData: metric });
  };

  const byAttempts = [...props.subjects].sort((a, b) => b.attempts - a.attempts);
  const byAccuracy = [...props.subjects].filter(s => s.accuracy != null)
    .sort((a, b) => (b.accuracy ?? 0) - (a.accuracy ?? 0));
  const chronological = [...props.attempts].sort((a, b) => a.local_date.localeCompare(b.local_date));
  const last = chronological[chronological.length - 1];

  // Last seven local dates, not "the last seven rows": a week is a span of
  // time, and seven attempts could be one afternoon.
  const weekAgo = new Date(Date.now() - 7 * 86400_000).toISOString().slice(0, 10);
  const thisWeek = chronological.filter(a => a.local_date >= weekAgo);
  const weekMarks = thisWeek.reduce((n, a) => n + (a.marks_awarded ?? 0), 0);
  const weekTotal = thisWeek.reduce((n, a) => n + (a.marks_total ?? 0), 0);

  push(StatCategory.OverallAccuracy, pct(props.totals.accuracy), `${props.totals.marksAwarded}/${props.totals.marksTotal}`);
  push(StatCategory.TotalPapersSolved, count(props.totals.papers), 'papers');
  push(StatCategory.TotalTimeSolving, duration(props.totals.timeMs), 'total');
  push(StatCategory.PracticeStreak, props.streaks.current ? `${props.streaks.current}` : null, `best ${props.streaks.longest}d`);
  push(StatCategory.MostAttemptedSubject, byAttempts[0]?.subject_code ?? null,
       byAttempts[0] ? `${byAttempts[0].attempts} papers` : null);
  push(StatCategory.StrongestSubject, byAccuracy[0]?.subject_code ?? null, pct(byAccuracy[0]?.accuracy));
  push(StatCategory.ThisWeeksAccuracy, weekTotal ? pct(weekMarks / weekTotal) : null, `${thisWeek.length} papers`);
  push(StatCategory.ThisWeeksSolvingTime,
       thisWeek.length ? duration(thisWeek.reduce((n, a) => n + (a.duration_ms ?? 0), 0)) : null, 'this week');
  push(StatCategory.FastestCompletionTime,
       chronological.length ? duration(Math.min(...chronological.map(a => a.duration_ms ?? Infinity))) : null, 'fastest paper');
  push(StatCategory.LongestSession,
       chronological.length ? duration(Math.max(...chronological.map(a => a.duration_ms ?? 0))) : null, 'longest paper');
  push(StatCategory.TimeSinceLastPaper,
       last ? `${Math.max(0, Math.round((Date.now() - new Date(`${last.local_date}T00:00:00`).getTime()) / 86400_000))}d` : null,
       'since last paper');

  return out;
});
</script>

<template>
  <div class="card-strip">
    <!-- rendered twice so the -50% keyframe lands on the start of the
         second copy and the loop is seamless. aria-hidden on the duplicate so
         a screen reader hears each statistic once. -->
    <StatsCard
      v-for="card in cards"
      :key="card.category"
      :category="card.category"
      :text="card.text"
      :metric-data="card.metricData"
    />
    <StatsCard
      v-for="card in cards"
      :key="`dup-${card.category}`"
      :category="card.category"
      :text="card.text"
      :metric-data="card.metricData"
      aria-hidden="true"
    />
  </div>
</template>

<style lang="scss" scoped>
/* the marquee is the original design and is kept. Two things about it were
   broken once the strip stopped being a fixed 30-card test array.

   `width: 500%` was a stand-in for "wider than the container". With 11 real
   cards it resolved to 7182px against a 1436px container, and because nothing
   clipped it the whole PAGE gained 5,500px of horizontal scroll. Width is now
   max-content - as wide as the cards actually are - and the container clips it
   (see .top-card-strip-container).

   `translateX(-50%)` only loops seamlessly if the content is exactly two
   copies of itself; against 500% it jumped. The template now renders the list
   twice, so -50% lands precisely on the start of the second copy. */
.card-strip {
    width: max-content;
    height: 100%;
    display: flex;
    column-gap: 10px;
    background-color: $background;
    animation: infinite-side-scroll 90s linear infinite;
}

/* a marquee that cannot be stopped is a problem for anyone reading the
   numbers on it. */
.card-strip:hover { animation-play-state: paused; }

@media (prefers-reduced-motion: reduce) {
    .card-strip { animation: none; }
}

@keyframes infinite-side-scroll {
    0%   { transform: translateX(0); }
    /* Half the doubled content plus half the gap that separates the two copies. */
    100% { transform: translateX(calc(-50% - 5px)); }
}
</style>