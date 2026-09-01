<script setup lang="ts">
// ==========================================================================
//
// The pseudocode IDE's section. docs/roadmap.md A4 recorded its absence:
// "ide_progress is not on it, so a user's pseudocode work is invisible beside
// their MCQ work, and 'accuracy' there silently means MCQ accuracy."
//
// WHY IT IS A SEPARATE SECTION AND NOT EXTRA TILES ON PROGRESS. The two are
// not the same measurement. A multiple-choice question is right or wrong
// against one key and carries a chance floor of 20-25%; a pseudocode answer is
// marked against a rubric of marking points, can be half right, and has no
// chance floor at all - a blank editor scores zero, where a blind guess on an
// MCQ paper scores a fifth. Averaging them would produce a number that means
// nothing, and putting them on one axis would invite the reader to do it
// themselves.
//
// EVERY FIGURE COMES FROM model.ts SS I. This component computes nothing; the
// one thing it decides is what to withhold, and it withholds by rendering the
// model's nulls as em dashes rather than by inventing a zero.
// ==========================================================================
import { computed } from 'vue';
import EChart from './EChart.vue';
import MicroStat from './MicroStat.vue';
import { baseAxis, baseTooltip, type ChartTheme } from '@/lib/charts/echarts';
import { pct, count } from '@/lib/stats/format';
import type { IdeReading, IdeSubmission } from '@/lib/stats/model';

const props = defineProps<{
  reading: IdeReading;
  submissions: IdeSubmission[];
}>();

const hasData = computed(() => props.reading.submissions > 0);

// Oldest first. Every submission is a point, including the ones that scored
// worse than the one before - that sequence is the entire reason the log
// exists, and smoothing it into a best-so-far line would draw a staircase that
// only ever goes up and describes nobody's actual practice.
const chronological = computed(() => [...props.submissions]
  .filter(s => s.max_marks > 0)
  .sort((a, b) => a.created_at.localeCompare(b.created_at)));

const scoreOption = computed(() => (theme: ChartTheme) => ({
  grid: { left: 44, right: 16, top: 16, bottom: 28 },
  tooltip: {
    ...baseTooltip(theme),
    trigger: 'axis',
    valueFormatter: (v: number) => `${Math.round(v * 100)}%`,
  },
  xAxis: {
    ...baseAxis(theme),
    type: 'category',
    // The submission ordinal, not the date: submissions cluster into a few
    // sittings, and a time axis would draw most of them on top of each other.
    data: chronological.value.map((_, i) => String(i + 1)),
    name: 'submission',
    nameLocation: 'middle',
    nameGap: 22,
    nameTextStyle: { color: theme.axis, fontFamily: theme.fontBody, fontSize: 11 },
  },
  yAxis: {
    ...baseAxis(theme),
    type: 'value',
    min: 0,
    max: 1,
    axisLabel: {
      color: theme.axis, fontFamily: theme.fontBody, fontSize: 11,
      formatter: (v: number) => `${Math.round(v * 100)}%`,
    },
  },
  series: [{
    type: 'line',
    showSymbol: chronological.value.length <= 40,
    symbolSize: 6,
    lineStyle: { width: 2, color: theme.series[0] },
    itemStyle: { color: theme.series[0] },
    data: chronological.value.map(s => s.score / s.max_marks),
  }],
}));

// Solved / attempted / untouched-but-submitted is a three-way split that a
// donut states in one glance and three tiles do not.
const outcomeOption = computed(() => (theme: ChartTheme) => {
  const solved = props.reading.solved;
  const unsolved = Math.max(props.reading.attempted - solved, 0);
  return {
    tooltip: { ...baseTooltip(theme), trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['58%', '82%'],
      avoidLabelOverlap: true,
      label: { show: false },
      data: [
        { value: solved, name: 'Solved', itemStyle: { color: theme.success } },
        { value: unsolved, name: 'Not yet solved', itemStyle: { color: theme.series[3] } },
      ].filter(d => d.value > 0),
    }],
  };
});

const trendText = computed(() => {
  const t = props.reading.trend;
  if (t === null) return null;
  return `${t >= 0 ? '+' : ''}${(t * 100).toFixed(1)}pt`;
});

const perSolveText = computed(() => {
  const n = props.reading.submissionsPerSolve;
  return n === null ? null : n.toFixed(1);
});

// The one place the section says something about its own limits: when the log
// came back truncated the model withholds the first-try rate, and the hint
// says why rather than leaving an unexplained dash.
const firstTryHint = computed(() => props.reading.complete
  ? `${props.reading.firstTrySolves} of ${props.reading.solved} solved`
  : 'needs the full history');
</script>

<template>
  <div class="ide-line-container panel">
    <h4 class="panel-title">Score per submission, in order</h4>
    <EChart
      class="panel-chart"
      :option="scoreOption"
      :has-data="hasData"
      label="pseudocode score history" />
  </div>
  <div class="ide-donut-container panel">
    <h4 class="panel-title">Questions</h4>
    <EChart
      class="panel-chart"
      :option="outcomeOption"
      :has-data="hasData"
      label="solved and unsolved questions" />
  </div>
  <div class="quickview-container ide-tile-1">
    <MicroStat
      label="Solved"
      :value="hasData ? `${reading.solved}/${reading.attempted}` : null"
      hint="questions attempted" />
  </div>
  <div class="quickview-container ide-tile-2">
    <MicroStat
      label="Marks"
      :value="reading.marksPossible ? `${reading.marksAwarded}/${reading.marksPossible}` : null"
      hint="best per question" />
  </div>
  <div class="quickview-container ide-tile-3">
    <MicroStat
      label="Submissions"
      :value="hasData ? count(reading.submissions) : null"
      hint="graded answers" />
  </div>
  <div class="quickview-container ide-tile-4">
    <MicroStat label="Per solve" :value="perSolveText" hint="submissions each" />
  </div>
  <div class="quickview-container ide-tile-5">
    <MicroStat
      label="First try"
      :value="pct(reading.firstTryRate)"
      :hint="firstTryHint" />
  </div>
  <div class="quickview-container ide-tile-6">
    <MicroStat label="Trend" :value="trendText" hint="latest vs earliest" />
  </div>
</template>

<style lang="scss" scoped>
// the same panel/tile skin as the Progress section, so this reads as one
// more section of the page rather than as a bolt-on.
.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-title {
  margin: 0 0 0.4rem;
  font-family: var(--font-body);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--muted);
}
.panel-chart { flex: 1 1 auto; min-height: 0; }

.ide-line-container {
  grid-column: 1/15;
  grid-row: 1/11;
  background-color: $secondary-background;
  border-radius: 20px;
}
.ide-donut-container {
  grid-column: 15/21;
  grid-row: 1/11;
  background-color: $secondary-background;
  border-radius: 20px;
}
/* Six tiles as two rows of three rather than one row of six: at a fifth of
   the page width a tile's label wraps and its value shrinks below the chart
   labels beside it. */
.ide-tile-1 { grid-column: 1/8;   grid-row: 11/16; }
.ide-tile-2 { grid-column: 8/15;  grid-row: 11/16; }
.ide-tile-3 { grid-column: 15/21; grid-row: 11/16; }
.ide-tile-4 { grid-column: 1/8;   grid-row: 16/21; }
.ide-tile-5 { grid-column: 8/15;  grid-row: 16/21; }
.ide-tile-6 { grid-column: 15/21; grid-row: 16/21; }
.quickview-container {
  background-color: $secondary-background;
  border-radius: 20px;
}
</style>
