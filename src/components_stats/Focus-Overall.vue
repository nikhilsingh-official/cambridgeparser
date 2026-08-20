<script setup lang="ts">
// ==========================================================================
//
// Focus section, redesigned. The original is preserved at tag
// `stats-page-original` and had two structural problems:
//   - every slot sat in columns 1-7 of a 20-column grid, leaving ~70% of the
//     section empty;
//   - four tiles all carried the class `quickview-container-1`, so they
//     stacked invisibly in one cell.
//
// This section drops the fixed 20x20 grid (Progress and Engagement keep
// theirs) because its content is two large charts plus a metric bar, and
// forcing that into 20 equal rows only makes the panel sizes arbitrary.
//
// The canvases below were deliberately left empty until the query layer had a
// consumer. It has one now (lib/stats/useStats.ts), so they are real charts.
// See docs/stats_page_design.md §3.1.
// ==========================================================================
import { computed } from 'vue';
import { Target, ScatterChart, Shuffle } from 'lucide-vue-next';
import EChart from './EChart.vue';
import { baseAxis, baseTooltip, type ChartTheme } from '@/lib/charts/echarts';
import { pct, duration, count } from '@/lib/stats/format';
import type { CalibrationPoint, FocusTotals, AnswerChangeSummary } from '@/lib/supabase/queries';
import type { QuestionFlagsView } from '@/lib/types/database';

const props = defineProps<{
  calibration: CalibrationPoint[];
  flags: QuestionFlagsView[];
  focus: FocusTotals;
  answerChanges: AnswerChangeSummary | null;
}>();

const hasData = computed(() => props.flags.length > 0);

// the six tiles under the charts. All six come from v_question_flags via
// summariseFlags(); a null value still renders a muted em dash rather than a
// zero, because "none recorded" and "measured zero" are different claims.
const tiles = computed(() => [
  { label: 'Overconfident',   value: count(props.focus.overconfident),  hint: 'sure, but wrong' },
  { label: 'Underconfident',  value: count(props.focus.underconfident), hint: 'right, but hesitant' },
  { label: 'Guesses',         value: count(props.focus.guesses),        hint: 'fast, no eliminations' },
  { label: 'Guess accuracy',  value: pct(props.focus.guessAccuracy),    hint: 'how often luck held' },
  { label: 'Questions',       value: count(props.focus.questions),      hint: 'in this selection' },
  { label: 'Median hesitation', value: duration(props.focus.medianHesitationMs), hint: 'before first action' },
]);

// ---------------------------------------------------------- answer changes
// A horizontal bar per outcome. Three magnitudes over one categorical axis,
// which is a bar chart; the net figure is a hero number beside it rather than a
// fourth bar, because it is a different quantity (a difference, not a count)
// and putting it on the same scale would invite reading it as one.
//
// Right-to-wrong is the bar that matters, so it is the status colour: this is
// the only chart on the page where one category is unambiguously bad.
const answerChangeOption = (theme: ChartTheme) => {
  const a = props.answerChanges!;
  return {
    grid: { top: 10, right: 60, bottom: 10, left: 116 },
    tooltip: {
      ...baseTooltip(theme), trigger: 'axis', axisPointer: { type: 'shadow' },
      valueFormatter: (v: number) => `${v} question${v === 1 ? '' : 's'}`,
    },
    xAxis: { type: 'value', ...baseAxis(theme), splitLine: { show: false }, axisLabel: { show: false } },
    yAxis: {
      type: 'category',
      data: ['Wrong → wrong', 'Right → wrong', 'Wrong → right'],
      ...baseAxis(theme), splitLine: { show: false },
      axisLabel: { ...baseAxis(theme).axisLabel, fontSize: 12 },
    },
    series: [{
      type: 'bar',
      barMaxWidth: 26,
      // Direct labels on every bar: three bars is few enough that a value on
      // each reads faster than an axis, and it satisfies the light-theme
      // contrast relief the palette validator asked for.
      label: {
        show: true, position: 'right', color: theme.text,
        fontFamily: theme.fontMono, fontSize: 12,
      },
      itemStyle: { borderRadius: [0, 4, 4, 0] },
      data: [
        { value: a.wrongToWrong, itemStyle: { color: theme.muted } },
        { value: a.rightToWrong, itemStyle: { color: theme.danger } },
        { value: a.wrongToRight, itemStyle: { color: theme.success } },
      ],
    }],
  };
};

// ------------------------------------------------------------- calibration
// Confidence on x, observed accuracy on y, against a y=x reference line.
// Points above the line mean you were righter than you felt.
const calibrationOption = (theme: ChartTheme) => ({
  grid: { top: 16, right: 18, bottom: 34, left: 44 },
  tooltip: {
    ...baseTooltip(theme), trigger: 'item',
    formatter: (p: { data: number[] }) =>
      `confidence ${(p.data[0]! * 100).toFixed(0)}%<br/>accuracy ${(p.data[1]! * 100).toFixed(0)}%<br/>${p.data[2]} questions`,
  },
  xAxis: {
    type: 'value', min: 0, max: 1, name: 'confidence', nameLocation: 'middle', nameGap: 22,
    nameTextStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 10 },
    ...baseAxis(theme),
    axisLabel: { ...baseAxis(theme).axisLabel, formatter: (v: number) => `${v * 100}%` },
  },
  yAxis: {
    type: 'value', min: 0, max: 1, ...baseAxis(theme),
    axisLabel: { ...baseAxis(theme).axisLabel, formatter: (v: number) => `${v * 100}%` },
  },
  series: [
    {
      type: 'line', smooth: 0.2, symbolSize: 9,
      lineStyle: { width: 2, color: theme.series[0] },
      // A 2px surface ring so overlapping points stay countable.
      itemStyle: { color: theme.series[0], borderWidth: 2, borderColor: theme.surface },
      data: props.calibration.map(c => [c.meanConfidence, c.observedAccuracy, c.questions]),
      markLine: {
        silent: true, symbol: 'none',
        // The y=x reference: perfect calibration. Recessive, dashed - it is
        // scaffolding, not a series.
        lineStyle: { color: theme.axis, width: 1, type: 'dashed', opacity: 0.6 },
        data: [[{ coord: [0, 0] }, { coord: [1, 1] }]],
      },
    },
  ],
});

// -------------------------------------------------------- time vs outcome
// Two marks, correct and incorrect, over time-spent. A status pair rather than
// two categorical hues: right/wrong is exactly the good/bad axis status
// colours exist for, and both carry a legend label so it is never colour alone.
const scatterOption = (theme: ChartTheme) => {
  const points = props.flags.filter(f => f.is_correct !== null && f.time_spent_ms != null);
  const toPoint = (f: QuestionFlagsView) => [
    Math.round((f.time_spent_ms ?? 0) / 1000),
    f.confidence ?? 0,
  ];
  return {
    grid: { top: 28, right: 18, bottom: 34, left: 44 },
    tooltip: {
      ...baseTooltip(theme), trigger: 'item',
      formatter: (p: { data: number[]; seriesName: string }) =>
        `${p.seriesName}<br/>${p.data[0]}s · confidence ${(p.data[1]! * 100).toFixed(0)}%`,
    },
    legend: {
      top: 0, left: 0, icon: 'circle', itemWidth: 8, itemHeight: 8,
      textStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 11 },
    },
    xAxis: {
      type: 'value', name: 'seconds', nameLocation: 'middle', nameGap: 22,
      nameTextStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 10 },
      ...baseAxis(theme),
    },
    yAxis: {
      type: 'value', min: 0, max: 1, ...baseAxis(theme),
      axisLabel: { ...baseAxis(theme).axisLabel, formatter: (v: number) => `${v * 100}%` },
    },
    series: [
      {
        name: 'Correct', type: 'scatter', symbolSize: 8,
        itemStyle: { color: theme.success, opacity: 0.55, borderWidth: 1, borderColor: theme.surface },
        data: points.filter(f => f.is_correct === true).map(toPoint),
      },
      {
        name: 'Incorrect', type: 'scatter', symbolSize: 8,
        itemStyle: { color: theme.danger, opacity: 0.55, borderWidth: 1, borderColor: theme.surface },
        data: points.filter(f => f.is_correct === false).map(toPoint),
      },
    ],
  };
};
</script>

<template>
  <div class="focus-layout">

    <!-- row 1 - the two charts that carry the section -->
    <div class="chart-row">
      <div class="panel calibration-panel">
        <div class="panel-header">
          <Target class="panel-icon" />
          <div>
            <h4>Calibration</h4>
            <!-- labelled "behavioural" deliberately - this is inferred from
                 timing and eliminations, not a confidence the student stated.
                 See docs/stats_page_design.md §0.2. -->
            <p class="panel-sub">behavioural confidence vs actual accuracy</p>
          </div>
        </div>
        <EChart class="chart-canvas" :option="calibrationOption" :has-data="hasData" label="calibration curve" />
        <p class="panel-legend">
          <span class="above"></span> above the line: you know more than you think
          <span class="below"></span> below: overconfident
        </p>
      </div>

      <div class="panel scatter-panel">
        <div class="panel-header">
          <ScatterChart class="panel-icon" />
          <div>
            <h4>Time vs correctness</h4>
            <p class="panel-sub">where your wrong answers come from</p>
          </div>
        </div>
        <EChart class="chart-canvas" :option="scatterOption" :has-data="hasData" label="time versus correctness" />
        <p class="panel-legend">
          fast &amp; unsure = guessing &nbsp;·&nbsp; slow &amp; sure = misconception
        </p>
      </div>
    </div>

    <!-- row 2 - full width. Empty until attempt_events is read; see §5. -->
    <div class="panel sankey-panel">
      <div class="panel-header">
        <Shuffle class="panel-icon" />
        <div>
          <h4>Answer changes</h4>
          <p class="panel-sub">first choice to final choice &mdash; is your instinct right?</p>
        </div>
      </div>
      <!-- built. attempt_events has recorded every option transition since
           it existed; v_answer_changes turns consecutive choices into verdicts
           against the answer key. Previously this panel said "not built yet". -->
      <div v-if="answerChanges" class="change-row">
        <EChart class="chart-canvas chart-canvas-wide" :option="answerChangeOption"
                :has-data="true" label="answer changes by outcome" />
        <div class="change-net" :class="answerChanges.netMarks >= 0 ? 'net-good' : 'net-bad'">
          <span class="net-value">{{ answerChanges.netMarks >= 0 ? '+' : '' }}{{ answerChanges.netMarks }}</span>
          <span class="net-label">marks, net</span>
          <span class="net-hint">
            across {{ answerChanges.changes }} change{{ answerChanges.changes === 1 ? '' : 's' }}
          </span>
        </div>
      </div>
      <div v-else class="chart-canvas chart-canvas-wide not-built">
        <p>No answer changes recorded</p>
        <p class="not-built-hint">
          This fills in once you have changed your mind on a question.
        </p>
      </div>
    </div>

    <!-- row 3 - metric bar -->
    <div class="tile-row">
      <div v-for="tile in tiles" :key="tile.label" class="tile">
        <p class="tile-label">{{ tile.label }}</p>
        <p class="tile-value" :class="{ empty: tile.value === null }">
          {{ tile.value ?? '—' }}
        </p>
        <p class="tile-hint">{{ tile.hint }}</p>
      </div>
    </div>

  </div>
</template>

<style lang="scss" scoped>
// honest empty state for the one panel with no metric behind it yet.
.change-row { display: flex; align-items: stretch; gap: 1rem; }
.change-row .chart-canvas { flex: 1 1 auto; min-width: 0; }

.change-net {
  flex: 0 0 auto;
  display: flex; flex-direction: column; justify-content: center; align-items: flex-end;
  padding-left: 1rem;
  border-left: 1px solid var(--border);
  .net-value { font-family: var(--font-mono); font-size: 2rem; line-height: 1; }
  .net-label { font-family: var(--font-body); font-size: 0.72rem; color: var(--muted); margin-top: 0.2rem; }
  .net-hint  { font-family: var(--font-body); font-size: 0.68rem; color: var(--muted); opacity: 0.75; }
}
.net-good .net-value { color: var(--success); }
.net-bad  .net-value { color: var(--danger); }

.not-built {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0.25rem; text-align: center;
  p { margin: 0; color: var(--muted); font-family: var(--font-body); font-size: 0.85rem; }
  .not-built-hint { font-size: 0.75rem; opacity: 0.7; max-width: 42ch; }
}

// a column flow rather than the 20x20 grid the other two sections use.
// grid-column/grid-row span the whole section body so this sits inside the
// parent grid without being governed by it.
.focus-layout {
  grid-column: 1 / 21;
  grid-row: 1 / 21;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

// same card treatment as the other sections - $secondary-background,
// 20px radius - so the redesign does not read as a different page.
.panel {
  background-color: $secondary-background;
  border-radius: 20px;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  column-gap: 12px;
  margin-bottom: 0.75rem;

  h4 {
    font-family: 'Inter';
    font-weight: 400;
    color: $text;
    margin: 0;
    font-size: 1.05rem;
  }
  .panel-sub {
    font-family: 'Lexend';
    font-size: 0.75rem;
    color: $text;
    opacity: 0.45;
    margin: 2px 0 0;
  }
  .panel-icon {
    width: 22px;
    height: 22px;
    color: $accent;
    flex-shrink: 0;
    margin-top: 2px;
  }
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  flex: 1 1 0;
  min-height: 0;
}

// the ECharts mount point. It must have a real height before init() - a
// flex/percentage height that resolves to 0 is the single most common reason
// an ECharts canvas renders blank.
.chart-canvas {
  flex: 1 1 auto;
  min-height: 220px;
  border-radius: 12px;
  // faint hatch marks the panel as awaiting data rather than broken.
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
  background-size: 24px 24px;
}
.chart-canvas-wide { min-height: 200px; }

.panel-legend {
  font-family: 'Lexend';
  font-size: 0.7rem;
  color: $text;
  opacity: 0.4;
  margin: 0.6rem 0 0;
  display: flex;
  align-items: center;
  column-gap: 6px;
  flex-wrap: wrap;

  .above, .below {
    width: 8px;
    height: 8px;
    border-radius: 2px;
    display: inline-block;
  }
  .above { background-color: $success; }
  .below { background-color: $danger; }
}

.sankey-panel { flex: 0 0 auto; }

.tile-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1rem;
  flex: 0 0 auto;
}

.tile {
  background-color: $secondary-background;
  border-radius: 20px;
  padding: 1rem 1.1rem;

  .tile-label {
    font-family: 'Lexend';
    font-size: 0.7rem;
    color: $text;
    opacity: 0.5;
    margin: 0;
  }
  .tile-value {
    font-family: 'Inter';
    font-size: 1.6rem;
    color: $text;
    margin: 4px 0 0;
    line-height: 1.1;
    // placeholder dash is dimmed so an unfilled tile never reads as a zero.
    &.empty { opacity: 0.25; }
  }
  .tile-hint {
    font-family: 'Lexend';
    font-size: 0.65rem;
    color: $accent;
    opacity: 0.55;
    margin: 4px 0 0;
  }
}

// below ~1100px six tiles across becomes unreadable.
@media (max-width: 1100px) {
  .chart-row { grid-template-columns: 1fr; }
  .tile-row  { grid-template-columns: repeat(3, 1fr); }
}
</style>
