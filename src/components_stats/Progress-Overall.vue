<script setup lang="ts">
// ==========================================================================
//
// Progress: how accuracy is moving, and what the marks are made of.
// Previously every slot in this grid rendered the literal word "microstat".
// The grid itself is unchanged - only the contents are new.
//
// Chart choices (dataviz skill, references/choosing-a-form.md):
//   - accuracy per subject over time -> LINE. Change over time with an
//     identity dimension; one line per subject, categorical colour.
//   - cumulative marks -> AREA over one series. A running total is magnitude,
//     and the filled area reads as accumulation where a bare line does not.
//   - outcome split -> DONUT, three parts of one whole that sum to 100%.
//     Three is at the top of what a donut can carry; a fourth would become a
//     bar chart.
// ==========================================================================
import { computed } from 'vue';
import EChart from './EChart.vue';
import MicroStat from './MicroStat.vue';
import { baseAxis, baseTooltip, type ChartTheme } from '@/lib/charts/echarts';
import { pct, count, shortDate } from '@/lib/stats/format';
import type { AttemptSummaryView, SubjectStatsView } from '@/lib/types/database';

const props = defineProps<{
  attempts: AttemptSummaryView[];
  subjects: SubjectStatsView[];
  totals: {
    papers: number; questions: number; marksAwarded: number; marksTotal: number;
    accuracy: number | null; timeMs: number; avgPaperMs: number | null;
  };
}>();

const hasData = computed(() => props.attempts.length > 0);

/** Attempts oldest-first; the views return newest-first for the recent list. */
const chronological = computed(() =>
  [...props.attempts].sort((a, b) => a.local_date.localeCompare(b.local_date)));

// The subjects actually present, in a STABLE order (most attempts first) so a
// subject keeps its colour slot when the filter changes. Colour follows the
// entity, never its rank within the current selection.
const subjectOrder = computed(() =>
  [...props.subjects].sort((a, b) => b.attempts - a.attempts).slice(0, 6));

const accuracyOption = (theme: ChartTheme) => {
  // A TIME axis, not a shared category axis of every date.
  //
  // The first version put all 46 dates on a category axis and gave each
  // subject a null on the dates it was not sat, with connectNulls. Each
  // subject has ~8 attempts, so that drew long flat runs between them - a
  // horizontal line reads as "accuracy held steady here", which is a claim
  // about days that contain no measurement at all. On a time axis each series
  // carries only its own points and the gaps stay gaps.
  const series = subjectOrder.value.map((s, i) => ({
    name: s.subject_name ?? s.subject_code,
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

const cumulativeOption = (theme: ChartTheme) => {
  let running = 0;
  const points = chronological.value.map(a => {
    running += a.marks_awarded ?? 0;
    return [a.local_date, running] as [string, number];
  });
  return {
    grid: { top: 18, right: 18, bottom: 26, left: 48 },
    tooltip: {
      ...baseTooltip(theme), trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: theme.axis, width: 1, type: 'dashed' } },
    },
    xAxis: { type: 'category', data: points.map(p => shortDate(p[0])), boundaryGap: false, ...baseAxis(theme), splitLine: { show: false } },
    yAxis: { type: 'value', ...baseAxis(theme) },
    series: [{
      name: 'Marks earned',
      type: 'line',
      smooth: 0.25,
      showSymbol: false,
      lineStyle: { width: 2, color: theme.series[0] },
      itemStyle: { color: theme.series[0] },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: theme.series[0] + '55' },
            { offset: 1, color: theme.series[0] + '05' },
          ],
        },
      },
      data: points.map(p => p[1]),
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

// the section's reading, from the same numbers the charts draw.

/** Accuracy of the newest five papers minus the oldest five, in points. */
const trend = computed(() => {
  const withAccuracy = chronological.value.filter(a => a.accuracy != null);
  if (withAccuracy.length < 6) return null;
  const take = Math.min(5, Math.floor(withAccuracy.length / 2));
  const mean = (xs: AttemptSummaryView[]) =>
    xs.reduce((n, a) => n + (a.accuracy ?? 0), 0) / xs.length;
  return mean(withAccuracy.slice(-take)) - mean(withAccuracy.slice(0, take));
});
</script>

<template>
    <div class="multi-line-container panel">
        <h4 class="panel-title">Accuracy by subject</h4>
        <EChart class="panel-chart" :option="accuracyOption" :has-data="hasData" label="accuracy history" />
    </div>
    <div class="progress-line-container panel">
        <h4 class="panel-title">Marks earned, cumulative</h4>
        <EChart class="panel-chart" :option="cumulativeOption" :has-data="hasData" label="cumulative marks" />
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
        <MicroStat label="Marks" :value="totals.marksTotal ? `${totals.marksAwarded}/${totals.marksTotal}` : null" hint="earned of available" />
    </div>
    <div class="quickview-container quickview-container-3">
        <MicroStat
          label="Trend"
          :value="trend === null ? null : `${trend >= 0 ? '+' : ''}${(trend * 100).toFixed(1)}pt`"
          hint="latest vs earliest" />
    </div>
    <div class="quickview-container quickview-container-1">
        <MicroStat label="Strongest" :value="bestSubject?.subject_name ?? null" :hint="pct(bestSubject?.accuracy) ?? 'no data'" />
    </div>
    <div class="quickview-container quickview-container-2">
        <MicroStat label="Weakest" :value="weakestSubject?.subject_name ?? null" :hint="pct(weakestSubject?.accuracy) ?? 'no data'" />
    </div>
</template>

<style lang="scss" scoped>

    // the containers below keep their original grid placement and skin.
    // These rules only add the internal layout the charts need - a title row
    // and a chart that fills the rest - because a chart in a box with no
    // height renders nothing and looks identical to a chart with no data.
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

    .multi-line-container {
        grid-column: 1/15;
        grid-row: 1/13;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .progress-line-container {
        grid-column: 3/21;
        grid-row: 13/21;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .donut-container {
        grid-column: 15/19;
        grid-row: 1/9;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .quickview-container-7 {
        grid-column: 15/17;
        grid-row: 9/13;
    }
    .quickview-container-6 {
        grid-column: 17/19;
        grid-row: 9/13;
    }
    .quickview-container-5 {
        grid-column: 19/21;
        grid-row: 1/5;
    }
    .quickview-container-4 {
        grid-column: 19/21;
        grid-row: 5/9;
    }
    .quickview-container-3 {
        grid-column: 19/21;
        grid-row: 9/13;
    }
    .quickview-container-1 {
        grid-column: 1/3;
        grid-row: 17/21;
    }
    .quickview-container-2 {
        grid-column: 1/3;
        grid-row: 13/17;
    }
    .quickview-container {
        background-color: $secondary-background;
        border-radius: 20px;
    }
</style>