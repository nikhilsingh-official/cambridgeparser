<script lang="ts" setup>
// this component's four rotating cards were invented figures - "Acccuracy
// (Total) 16", "Confidence 12", "Difficulty 5", "Interest 3". Two of those
// four had no data behind them anywhere in the app, and none of the numbers
// was the reader's.
//
// The replacements are the four things this page can honestly say, all
// week-over-week from lib/stats/model.ts. They are all "up is good" on
// purpose: the SCSS below hardwires .feather-arrow-up green and
// .feather-arrow-down red, so a metric where falling is an improvement would
// be painted as a failure.
//
// The markup, the classes, the rotation and the whole <style> block are as
// they were; the four literal cards became a v-for over the same four slots.
import { computed, onMounted, onUnmounted, ref } from 'vue';
// the preview now opens the full statistics page.
import { RouterLink } from 'vue-router';
import { duration, count } from '@/lib/stats/format';
// each tile now carries a real fourteen-day series into its mini-chart.
import MiniTrend from './MiniTrend.vue';
import type { DailyActivitySeries, Movement, RecentActivity } from '@/lib/stats/model';

const props = defineProps<{
  recent: RecentActivity | null;
  series: DailyActivitySeries;
  loading: boolean;
}>();

const DASH = '\u2014';

// The rotation is driven by moving these class names between the four nodes,
// so the slots are positional and fixed. Bound rather than literal only so the
// cards can be a v-for - the string never changes, so Vue never writes the
// class attribute again after mount and the animation keeps its own state.
const SLOTS = [
  'active',
  'inactive-1 inactive',
  'inactive-2 inactive',
  'inactive-3 inactive',
];

interface Card {
  label: string;
  value: string;
  change: string | null;
  /** true up, false down, null when there is nothing to compare against. */
  up: boolean | null;
  series: Array<number | null>;
  color: string;
}

// Someone in their first week has no previous week. Showing their running
// total under a green arrow would dress a starting figure as growth, so an
// incomparable movement shows the plain current figure and no arrow at all -
// and so does a flat week, where an arrow would have to point somewhere.
// keep headline values, deltas, visual series, and theme colour together.
function card(
  label: string,
  m: Movement,
  valueFormat: (n: number) => string,
  deltaFormat: (n: number) => string,
  series: Array<number | null>,
  color: string,
): Card {
  if (props.loading) return { label, value: DASH, change: null, up: null, series: [], color };
  if (!m.comparable) {
    return { label, value: valueFormat(m.current), change: null, up: null, series, color };
  }
  return {
    label,
    // the headline is the current seven-day value. The old implementation
    // showed only the delta, so two active weeks could misleadingly read "0".
    value: valueFormat(m.current),
    change: m.delta === 0 ? 'no change' : deltaFormat(Math.abs(m.delta)),
    up: m.delta === 0 ? null : m.delta > 0,
    series,
    color,
  };
}

const NOTHING: Movement = { current: 0, previous: 0, delta: 0, comparable: false };

const cards = computed<Card[]>(() => {
  const r = props.recent;
  // Accuracy moves in ratio, so its delta is reported in percentage points -
  // "4 pts", never "4%", which would read as a relative change.
  // every rotating card receives its corresponding fourteen-day series.
  return [
    card('Accuracy (7d)', r?.accuracy ?? NOTHING,
      n => `${Math.round(n * 100)}%`, n => `${Math.round(n * 100)} pts`,
      props.series.accuracy, 'var(--series-1)'),
    card('Papers (7d)', r?.papers ?? NOTHING,
      n => count(n) ?? '0', n => count(n) ?? '0',
      props.series.papers, 'var(--series-2)'),
    card('Questions (7d)', r?.questions ?? NOTHING,
      n => count(n) ?? '0', n => count(n) ?? '0',
      props.series.questions, 'var(--series-3)'),
    card('Time (7d)', r?.timeMs ?? NOTHING,
      n => duration(n) ?? '0m', n => duration(n) ?? '0m',
      props.series.timeMs, 'var(--series-4)'),
  ];
});

// the interval was never cleared. After navigating away the queries below
// returned null and .classList threw every ten seconds for the rest of the
// session; the null guard covers the same hazard on the first tick.
let timer: ReturnType<typeof setInterval> | undefined;
// scope animation queries to this component. A global `.active` query
// could rotate an unrelated active button elsewhere on the dashboard.
const previewRef = ref<HTMLElement | null>(null);

onMounted(() => {
    timer = setInterval(() => {
      const inactiveItem1 = previewRef.value?.querySelector(".inactive-1");
      const inactiveItem2 = previewRef.value?.querySelector(".inactive-2");
      const inactiveItem3 = previewRef.value?.querySelector(".inactive-3");
      const activeItem = previewRef.value?.querySelector(".active");
      if (!inactiveItem1 || !inactiveItem2 || !inactiveItem3 || !activeItem) return;

      activeItem.classList.add("inactive-3", "inactive");
      activeItem.classList.remove("active");

      inactiveItem1.classList.add("active");
      inactiveItem1.classList.remove("inactive-1", "inactive");

      inactiveItem2.classList.add("inactive-1");
      inactiveItem2.classList.remove("inactive-2");

      inactiveItem3.classList.add("inactive-2");
      inactiveItem3.classList.remove("inactive-3");
    }, 10000);
})

onUnmounted(() => clearInterval(timer))

</script>
<template>
    <!-- this panel advertised clickability without doing anything. -->
    <RouterLink to="/stats" class="stats-preview" aria-label="Open statistics">
        <h1 class = "stats-header"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-bar-chart-2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg> <span>&middot;</span> stats</h1>
        <div ref="previewRef" class = "preview-container">
            <div v-for="(tile, i) in cards" :key="tile.label" class="item" :class="SLOTS[i]">
                <div class="label">{{ tile.label }}</div>
                <div class="metadata">
                  <strong>{{ tile.value }}</strong>
                  <span v-if="tile.change" class="change">
                    <svg v-if="tile.up !== null" xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather" :class="tile.up ? 'feather-arrow-up' : 'feather-arrow-down'"><line x1="12" :y1="tile.up ? 19 : 5" x2="12" :y2="tile.up ? 5 : 19"></line><polyline :points="tile.up ? '5 12 12 5 19 12' : '19 12 12 19 5 12'"></polyline></svg>
                    {{ tile.change }}
                  </span>
                </div>
                <!-- the panel now contains the trend plots it visually promised. -->
                <MiniTrend :values="tile.series" :label="tile.label" :color="tile.color" />
            </div>
        </div>
    </RouterLink>
</template>
<style lang="scss" scoped>
.stats-preview {
  grid-row: 13 / 20;
  grid-column: 4 / 13;
  background-color: $secondary-background;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  background-image:
    linear-gradient(to right, $background 1px, transparent 1px),
    linear-gradient(to bottom, $background 1px, transparent 1px);  background-size: 30px 30px;
  background-repeat: repeat;
  cursor: pointer;
  color: inherit;
  text-decoration: none;
}

.stats-header {
  font-family: 'Inter';
  font-weight: 300;
  font-size: 20px;
  width: 100%;
  height: fit-content;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
  padding-left: 1rem;
  padding-right: 1rem;
  display: flex;
  align-items: center;
  column-gap: 10px;
  span {
    font-size: 10px;
  }
  svg {
    color: $accent;
  }
}

.preview-container {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 10px;
}

.item {
  font-family: 'Lexend';
  font-size: 13px;
  position: absolute;
  overflow: hidden;
  transform: translate(-50%,-50%);
  transition: left 1s ease-in-out, top 1s ease-in-out, width 1s ease-in-out, height 1s ease-in-out, scale 1s ease;
  cursor: pointer;
  &:hover {
    scale: 1.01;
  }
}

.inactive {
  left: calc(87.5% - 0.5rem);
  width: calc(25% - 1rem);
  height: 24%;
  border-radius: 10px;
}

.inactive-1 {
  top: 20%;
}

.inactive-2 {
  top: 50%;
}

.inactive-3 {
  top: 80%;
}

.active {
  left: 37.5%;
  top: 50%;
  width: calc(75% - 2rem);
  height: calc(100% - 2rem);
  border-radius: 10px;
}

.metadata {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  /* separate the current value from its compact comparison. */
  gap: 0.5rem;
  transition: opacity 1s ease;
  background-color: rgba(0, 0, 0, 0.1);
  /* semantic theme tokens replace the old fixed red/neon arrow colours. */
  .feather-arrow-up {
    color: var(--success);
  }
  .feather-arrow-down {
    color: var(--danger);
  }
}

/* keep the compact comparison subordinate to the current-week value. */
.change {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  color: var(--muted);
  font-size: 0.68rem;
}

/* every card keeps its trend visible. Inactive cards reserve the bottom
   label band and render a compact sparkline; only the active card expands to
   the full chart with its date labels. */
.inactive :deep(.mini-trend) {
  inset: 0.4rem 0.55rem calc(30px + 0.4rem);
  opacity: 1;
  transition: inset 1s ease-in-out;
}

.active :deep(.mini-trend) {
  inset: 3.4rem 1rem 1rem;
  opacity: 1;
  transition: inset 1s ease-in-out;
}

/* compact cards have too little vertical space for axis captions or the
   no-data sentence; the graph itself remains visible in every state. */
.inactive :deep(.mini-trend > small),
.inactive :deep(.mini-trend > span) {
  display: none;
}

.label {
  position: absolute;
  height: 30px;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: top 1s ease, left 1s ease, width 1s ease;
  background-color: rgba(0, 0, 0, 0.1);
}

.active .label {
  top: 0;
  width: 30%;
  border-bottom-right-radius: inherit;
  padding: 1rem;
}

.inactive .label {
  top: calc(100% - 30px);
  width: 100%;
}

.active .metadata {
  padding: 1rem;
  height: 30px;
  width: fit-content;
  border-bottom-left-radius: inherit;
  opacity: 1;
}

.inactive .metadata {
  opacity: 0;
}
</style>
