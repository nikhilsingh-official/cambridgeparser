<script setup lang="ts">
// ==========================================================================
//
// Progress: how each completed paper scored, and how subjects are moving.
// Previously every slot in this grid rendered the literal word "microstat".
// The grid itself is unchanged - only the contents are new.
//
// Chart choices (dataviz skill, references/choosing-a-form.md):
//   - each paper's raw score over time -> LINE. The y-axis normalises papers
//     with different totals, while labels/tooltips retain marks such as 34/40.
//   - accuracy per subject over time -> LINE. Change over time with an
//     identity dimension; one line per subject, categorical colour.
//   - outcome split -> DONUT, three parts of one whole that sum to 100%.
//     Three is at the top of what a donut can carry; a fourth would become a
//     bar chart.
// ==========================================================================
import { computed } from 'vue';
import EChart from './EChart.vue';
import MicroStat from './MicroStat.vue';
import { baseAxis, baseTooltip, type ChartTheme } from '@/lib/charts/echarts';
import { pct, count, shortDate, subjectLabel } from '@/lib/stats/format';
import type { AttemptSummaryView, SubjectStatsView } from '@/lib/types/database';
import { accuracyTrend } from '@/lib/stats/model';

const props = defineProps<{
  attempts: AttemptSummaryView[];
  subjects: SubjectStatsView[];
  subjectScoped: boolean;
  totals: {
    papers: number; questions: number; marksAwarded: number; marksTotal: number;
    accuracy: number | null; timeMs: number; avgPaperMs: number | null;
  };
}>();

const hasData = computed(() => props.attempts.length > 0);

/** Attempts oldest-first; the views return newest-first for the recent list. */
const chronological = computed(() =>
  [...props.attempts].sort((a, b) => a.local_date.localeCompare(b.local_date)));

const scoredAttempts = computed(() => chronological.value.filter(attempt =>
  attempt.marks_total > 0 && attempt.accuracy !== null));

// The subjects actually present, in a STABLE order (most attempts first) so a
// subject keeps its colour slot when the filter changes. Colour follows the
// entity, never its rank within the current selection.
const subjectOrder = computed(() =>
  [...props.subjects].sort((a, b) => b.attempts - a.attempts).slice(0, 6));

const subjectTrendOption = (theme: ChartTheme) => {
  // A TIME axis, not a shared category axis of every date.
  //
  // The first version put all 46 dates on a category axis and gave each
  // subject a null on the dates it was not sat, with connectNulls. Each
  // subject has ~8 attempts, so that drew long flat runs between them - a
  // horizontal line reads as "accuracy held steady here", which is a claim
  // about days that contain no measurement at all. On a time axis each series
  // carries only its own points and the gaps stay gaps.
  const series = subjectOrder.value.map((s, i) => ({
    name: subjectLabel(s, props.subjects),
    type: 'line',
    smooth: false,
    showSymbol: true,
    symbolSize: 7,
    lineStyle: { width: 2, color: theme.series[i] },
    itemStyle: { color: theme.series[i], borderWidth: 2, borderColor: theme.surface },
    data: chronological.value
      .filter(a => a.subject_code === s.subject_code && a.accuracy != null)
      .map(a => [a.local_date, +(a.accuracy! * 100).toFixed(1)]),
  }));

  return {
    color: theme.series,
    grid: { top: 34, right: 18, bottom: 26, left: 44 },
    // Crosshair tooltip: an HTML chart is interactive by default, and a line
    // chart without one makes the reader guess at values between labels.
    tooltip: {
      ...baseTooltip(theme),
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: theme.axis, width: 1, type: 'dashed' } },
      valueFormatter: (v: number) => (v == null ? '—' : `${v}%`),
    },
    legend: {
      top: 4, left: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
      // Legend text wears TEXT tokens, never the series colour - the swatch
      // beside it already carries identity.
      textStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 11 },
    },
    xAxis: {
      type: 'time', ...baseAxis(theme), splitLine: { show: false },
      axisLabel: { ...baseAxis(theme).axisLabel, formatter: (v: number) => shortDate(new Date(v).toISOString().slice(0, 10)) },
    },
    yAxis: { type: 'value', min: 0, max: 100, ...baseAxis(theme), axisLabel: { ...baseAxis(theme).axisLabel, formatter: '{value}%' } },
    series,
  };
};

const componentTrendOption = (theme: ChartTheme) => {
  const paperNumbers = [...new Set(scoredAttempts.value.map(attempt => attempt.paper_number))]
    .sort((a, b) => (a ?? Number.MAX_SAFE_INTEGER) - (b ?? Number.MAX_SAFE_INTEGER));
  const series = paperNumbers.map((paperNumber, index) => ({
    name: paperNumber === null ? 'Unknown component' : `Paper ${paperNumber}`,
    type: 'line',
    smooth: false,
    showSymbol: true,
    symbolSize: 7,
    lineStyle: { width: 2, color: theme.series[index] },
    itemStyle: { color: theme.series[index], borderWidth: 2, borderColor: theme.surface },
    data: scoredAttempts.value
      .filter(attempt => attempt.paper_number === paperNumber)
      .map(attempt => [attempt.local_date, +(attempt.accuracy! * 100).toFixed(1)]),
  }));

  return {
    color: theme.series,
    grid: { top: 34, right: 18, bottom: 26, left: 44 },
    tooltip: {
      ...baseTooltip(theme),
      trigger: 'axis',
      valueFormatter: (value: number) => `${value}%`,
    },
    legend: {
      top: 4, left: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10,
      textStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 11 },
    },
    xAxis: {
      type: 'time', ...baseAxis(theme), splitLine: { show: false },
      axisLabel: { ...baseAxis(theme).axisLabel, formatter: (value: number) => shortDate(new Date(value).toISOString().slice(0, 10)) },
    },
    yAxis: { type: 'value', min: 0, max: 100, ...baseAxis(theme), axisLabel: { ...baseAxis(theme).axisLabel, formatter: '{value}%' } },
    series,
  };
};

const paperScoresOption = (theme: ChartTheme) => {
  const colourBySubject = new Map(
    subjectOrder.value.map((subject, index) => [subject.subject_code, theme.series[index]]),
  );
  const points = scoredAttempts.value;

  return {
    grid: { top: points.length <= 12 ? 32 : 18, right: 18, bottom: 34, left: 48 },
    tooltip: {
      ...baseTooltip(theme),
      trigger: 'item',
      axisPointer: { type: 'line', lineStyle: { color: theme.axis, width: 1, type: 'dashed' } },
      formatter: (p: { data: { paper: string; subject: string; date: string; score: string; value: number } }) =>
        `${p.data.paper}<br/>${p.data.subject}<br/>${shortDate(p.data.date)} · <b>${p.data.score}</b> (${p.data.value.toFixed(1)}%)`,
    },
    xAxis: {
      type: 'category',
      data: points.map(attempt => shortDate(attempt.local_date)),
      boundaryGap: false,
      ...baseAxis(theme),
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value', min: 0, max: 100, ...baseAxis(theme),
      axisLabel: { ...baseAxis(theme).axisLabel, formatter: '{value}%' },
    },
    series: [{
      name: 'Paper score',
      type: 'line',
      smooth: false,
      showSymbol: true,
      symbolSize: 8,
      lineStyle: { width: 2, color: theme.axis, opacity: 0.65 },
      label: {
        show: points.length <= 12,
        position: 'top',
        color: theme.text,
        fontFamily: theme.fontMono,
        fontSize: 10,
        formatter: (p: { data: { score: string } }) => p.data.score,
      },
      data: points.map(attempt => ({
        value: +(attempt.accuracy! * 100).toFixed(1),
        paper: attempt.paper_id,
        subject: subjectLabel(attempt, props.subjects),
        date: attempt.local_date,
        score: `${attempt.marks_awarded}/${attempt.marks_total}`,
        itemStyle: {
          color: colourBySubject.get(attempt.subject_code) ?? theme.series[0],
          borderColor: theme.surface,
          borderWidth: 2,
        },
      })),
    }],
  };
};

const outcome = computed(() => {
  const correct = props.attempts.reduce((n, a) => n + (a.questions_correct ?? 0), 0);
  const recorded = props.attempts.reduce((n, a) => n + (a.questions_recorded ?? 0), 0);
  const answered = props.attempts.reduce((n, a) => n + (a.questions_answered ?? 0), 0);
  return { correct, wrong: Math.max(0, answered - correct), blank: Math.max(0, recorded - answered) };
});

const donutOption = (theme: ChartTheme) => ({
  tooltip: { ...baseTooltip(theme), trigger: 'item', valueFormatter: (v: number) => `${v} questions` },
  legend: {
    bottom: 0, left: 'center', icon: 'circle', itemWidth: 8, itemHeight: 8,
    textStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 11 },
  },
  series: [{
    type: 'pie',
    radius: ['58%', '80%'],
    center: ['50%', '44%'],
    avoidLabelOverlap: true,
    // A 2px surface gap between segments, so adjacent fills read as separate
    // marks rather than one continuous ring.
    itemStyle: { borderColor: theme.surface, borderWidth: 2, borderRadius: 3 },
    label: { show: false },
    labelLine: { show: false },
    data: [
      // Correct/incorrect is a STATUS pair, not two categorical series: it is
      // a good/bad outcome and reads instantly in those colours. Both ship
      // with a legend label, never colour alone.
      { value: outcome.value.correct, name: 'Correct', itemStyle: { color: theme.success } },
      { value: outcome.value.wrong, name: 'Incorrect', itemStyle: { color: theme.danger } },
      { value: outcome.value.blank, name: 'Unanswered', itemStyle: { color: theme.muted } },
    ].filter(d => d.value > 0),
  }],
});

const bestSubject = computed(() => {
  const ranked = [...props.subjects].filter(s => s.accuracy != null)
    .sort((a, b) => (b.accuracy ?? 0) - (a.accuracy ?? 0));
  return ranked[0] ?? null;
});
const weakestSubject = computed(() => {
  const ranked = [...props.subjects].filter(s => s.accuracy != null)
    .sort((a, b) => (a.accuracy ?? 0) - (b.accuracy ?? 0));
  return ranked[0] ?? null;
});

const bestAttempt = computed(() => [...scoredAttempts.value]
  .sort((a, b) => (b.accuracy ?? 0) - (a.accuracy ?? 0))[0] ?? null);
const latestScoredAttempt = computed(() =>
  scoredAttempts.value[scoredAttempts.value.length - 1] ?? null);

// the section's reading, from the same numbers the charts draw.

/**
 * Accuracy of the newest papers minus the oldest, in ratio.
 *
 * the arithmetic moved to model.ts. It was written out here AND in
 * StatsPage.vue, which fed the recommendation banner - so the chart and the
 * sentence above it were two independent implementations of the same claim.
 */
const trend = computed(() => accuracyTrend(chronological.value));
</script>

<template>
  <div class="multi-line-container panel">
    <h4 class="panel-title">Paper scores over time</h4>
    <EChart class="panel-chart" :option="paperScoresOption" :has-data="hasData" label="paper score history" />
    <div v-if="scoredAttempts.length" class="score-sequence" aria-label="Raw paper score sequence">
      <span v-for="attempt in scoredAttempts" :key="attempt.id">
        <strong>{{ attempt.marks_awarded }}/{{ attempt.marks_total }}</strong>
        <small>{{ attempt.paper_id }}</small>
      </span>
    </div>
  </div>
  <div class="progress-line-container panel">
    <h4 class="panel-title">{{ subjectScoped ? 'Trend by paper component' : 'Improvement by subject' }}</h4>
    <EChart
      class="panel-chart"
      :option="subjectScoped ? componentTrendOption : subjectTrendOption"
      :has-data="hasData"
      :label="subjectScoped ? 'paper component score history' : 'subject score history'" />
  </div>
  <div class="donut-container panel">
    <h4 class="panel-title">Outcomes</h4>
    <EChart class="panel-chart" :option="donutOption" :has-data="hasData" label="answer outcomes" />
  </div>
  <div class="quickview-container quickview-container-7">
    <MicroStat label="Accuracy" :value="pct(totals.accuracy)" hint="marks ÷ total" />
  </div>
  <div class="quickview-container quickview-container-6">
    <MicroStat label="Papers" :value="count(totals.papers)" hint="completed" />
  </div>
  <div class="quickview-container quickview-container-5">
    <MicroStat label="Questions" :value="count(totals.questions)" hint="answered" />
  </div>
  <div class="quickview-container quickview-container-4">
    <MicroStat label="Marks" :value="totals.marksTotal ? `${totals.marksAwarded}/${totals.marksTotal}` : null" hint="earned / available" />
  </div>
  <div class="quickview-container quickview-container-3">
    <MicroStat
      label="Trend"
      :value="trend === null ? null : `${trend >= 0 ? '+' : ''}${(trend * 100).toFixed(1)}pt`"
      hint="latest vs earliest" />
  </div>
  <div class="quickview-container quickview-container-1">
    <MicroStat
      :label="subjectScoped ? 'Best paper' : 'Strongest'"
      :value="subjectScoped && bestAttempt ? `${bestAttempt.marks_awarded}/${bestAttempt.marks_total}` : bestSubject ? subjectLabel(bestSubject, subjects) : null"
      :hint="subjectScoped ? bestAttempt?.paper_id ?? 'no data' : pct(bestSubject?.accuracy) ?? 'no data'" />
  </div>
  <div class="quickview-container quickview-container-2">
    <MicroStat
      :label="subjectScoped ? 'Latest paper' : 'Weakest'"
      :value="subjectScoped && latestScoredAttempt ? `${latestScoredAttempt.marks_awarded}/${latestScoredAttempt.marks_total}` : weakestSubject ? subjectLabel(weakestSubject, subjects) : null"
      :hint="subjectScoped ? latestScoredAttempt?.paper_id ?? 'no data' : pct(weakestSubject?.accuracy) ?? 'no data'" />
  </div>
</template>

<style lang="scss" scoped>
// these containers retain the dashboard grid while using shared theme
// tokens for every visible surface.
.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0.85rem 0.9rem 0.7rem;
  box-sizing: border-box;
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

.score-sequence {
  display: flex;
  flex: 0 0 auto;
  gap: 0.45rem;
  max-width: 100%;
  padding: 0.55rem 0.1rem 0;
  overflow-x: auto;
  scrollbar-width: thin;
}
.score-sequence > span {
  display: grid;
  flex: 0 0 auto;
  gap: 0.08rem;
  min-width: 4.2rem;
  padding: 0.35rem 0.45rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  background: var(--tertiary-background);
}
.score-sequence strong {
  color: var(--text);
  font: 600 0.7rem var(--font-mono);
}
.score-sequence small {
  max-width: 7rem;
  overflow: hidden;
  color: var(--muted);
  font: 0.52rem var(--font-mono);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.multi-line-container {
  grid-column: 1/15;
  grid-row: 1/13;
  background-color: var(--secondary-background);
  border-radius: var(--radius-card);
}
.progress-line-container {
  grid-column: 3/21;
  grid-row: 13/21;
  background-color: var(--secondary-background);
  border-radius: var(--radius-card);
}
.donut-container {
  grid-column: 15/19;
  grid-row: 1/9;
  background-color: var(--secondary-background);
  border-radius: var(--radius-card);
}
.quickview-container-7 { grid-column: 15/17; grid-row: 9/13; }
.quickview-container-6 { grid-column: 17/19; grid-row: 9/13; }
.quickview-container-5 { grid-column: 19/21; grid-row: 1/5; }
.quickview-container-4 { grid-column: 19/21; grid-row: 5/9; }
.quickview-container-3 { grid-column: 19/21; grid-row: 9/13; }
.quickview-container-1 { grid-column: 1/3; grid-row: 17/21; }
.quickview-container-2 { grid-column: 1/3; grid-row: 13/17; }
.quickview-container {
  background-color: var(--secondary-background);
  border-radius: var(--radius-card);
}
</style>
