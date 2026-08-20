<script setup lang="ts">
// ==========================================================================
//
// Engagement: when the work happens, and how consistently.
// Every slot here rendered the literal word "microstat" or "heatmap" before.
//
// Chart choices (dataviz skill, references/choosing-a-form.md):
//   - daily activity -> HEATMAP over a calendar. Magnitude across two
//     categorical axes (week, weekday); the only form that shows consistency
//     and gaps at a glance, which is the question this section answers.
//     Sequential ramp, ONE hue, light to dark - never a rainbow.
//   - time per session -> BAR. Discrete sessions, magnitude, no continuity
//     between them, so bars rather than a line.
//   - hour of day -> a TILE, not a chart. The section's grid has no free
//     slot, and 'when do you revise' has a one-value answer; v_hour_of_day
//     is read for that tile rather than left unconsumed.
//   - the session list -> TABLE. Discrete records with several attributes
//     each; a chart would encode less and read slower.
// ==========================================================================
import { computed } from 'vue';
import EChart from './EChart.vue';
import MicroStat from './MicroStat.vue';
import { baseAxis, baseTooltip, type ChartTheme } from '@/lib/charts/echarts';
import { duration, shortDate, pct, subjectLabel } from '@/lib/stats/format';
import type { AttemptSummaryView, DailyActivityView, HourOfDayView } from '@/lib/types/database';

const props = defineProps<{
  attempts: AttemptSummaryView[];
  daily: DailyActivityView[];
  hours: HourOfDayView[];
  streaks: { current: number; longest: number };
  totals: { papers: number; timeMs: number; avgPaperMs: number | null };
}>();

const hasData = computed(() => props.attempts.length > 0);

// ---------------------------------------------------------------- heatmap
/** Every date from the first activity to today, so gaps are visible as gaps. */
const calendar = computed(() => {
  if (props.daily.length === 0) return [] as { date: string; minutes: number }[];
  const byDate = new Map(props.daily.map(d => [d.local_date, d.total_time_ms ?? 0]));
  const start = new Date(`${props.daily.reduce((m, d) => d.local_date < m ? d.local_date : m, props.daily[0]!.local_date)}T00:00:00`);
  const end = new Date();
  const out: { date: string; minutes: number }[] = [];
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const iso = d.toISOString().slice(0, 10);
    out.push({ date: iso, minutes: Math.round((byDate.get(iso) ?? 0) / 60000) });
  }
  return out;
});

const heatmapOption = (theme: ChartTheme) => {
  const days = calendar.value;
  if (days.length === 0) return {};
  // Monday-first weeks. getDay() is Sunday-based, so shift it.
  const weekdayOf = (iso: string) => (new Date(`${iso}T00:00:00`).getDay() + 6) % 7;
  const startOffset = weekdayOf(days[0]!.date);
  const data = days.map((d, i) => {
    const week = Math.floor((i + startOffset) / 7);
    return [week, weekdayOf(d.date), d.minutes, d.date];
  });
  const weeks = Math.max(...data.map(d => d[0] as number)) + 1;
  const max = Math.max(1, ...days.map(d => d.minutes));

  return {
    grid: { top: 8, right: 8, bottom: 44, left: 34, height: 'auto' },
    tooltip: {
      ...baseTooltip(theme),
      formatter: (p: { data: (string | number)[] }) => {
        const [, , minutes, date] = p.data;
        return `${shortDate(String(date))}<br/>${minutes ? `${minutes} min` : 'no revision'}`;
      },
    },
    xAxis: { type: 'category', data: Array.from({ length: weeks }, (_, i) => i), show: false },
    yAxis: {
      type: 'category',
      data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      inverse: true,
      ...baseAxis(theme),
      splitLine: { show: false },
      axisLabel: { ...baseAxis(theme).axisLabel, fontSize: 9, interval: 1 },
    },
    visualMap: {
      min: 0, max, calculable: false, orient: 'horizontal', left: 34, bottom: 6,
      itemWidth: 10, itemHeight: 70,
      // `dimension` is NOT optional here. Each row is
      // [week, weekday, minutes, date] and visualMap defaults to the LAST
      // dimension - so it mapped colour off the date string, every cell fell
      // outside the numeric range, and the whole calendar rendered in the
      // ramp's darkest step. It looked like a chart with no data while holding
      // 46 populated days.
      dimension: 2,
      // Sequential: one hue, light to dark. Zero gets the lowest step so an
      // empty day still reads as a cell rather than a hole in the grid.
      inRange: { color: theme.sequential },
      textStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 10 },
      text: [`${max}m`, '0'],
    },
    series: [{
      type: 'heatmap',
      data,
      // A 2px surface gap between cells: adjacent fills must read as separate
      // marks, which for a heatmap is the difference between a calendar and a
      // gradient.
      itemStyle: { borderColor: theme.surface, borderWidth: 2, borderRadius: 2 },
      progressive: 0,
    }],
  };
};

// ------------------------------------------------------------ session time
const sessionOption = (theme: ChartTheme) => {
  const recent = [...props.attempts]
    .sort((a, b) => a.local_date.localeCompare(b.local_date))
    .slice(-24);
  return {
    grid: { top: 14, right: 14, bottom: 26, left: 44 },
    tooltip: {
      ...baseTooltip(theme), trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (v: number) => `${v} min`,
    },
    xAxis: { type: 'category', data: recent.map(a => shortDate(a.local_date)), ...baseAxis(theme), splitLine: { show: false } },
    yAxis: { type: 'value', ...baseAxis(theme), axisLabel: { ...baseAxis(theme).axisLabel, formatter: '{value}m' } },
    series: [{
      type: 'bar',
      name: 'Minutes',
      barMaxWidth: 18,
      // 4px rounded data-ends, anchored to the baseline: the growing end is
      // rounded, the baseline end stays square so the bar sits on the axis.
      itemStyle: { color: theme.series[0], borderRadius: [4, 4, 0, 0] },
      data: recent.map(a => Math.round((a.duration_ms ?? 0) / 60000)),
    }],
  };
};

// -------------------------------------------------------------- session log
const sessions = computed(() =>
  [...props.attempts]
    .sort((a, b) => b.local_date.localeCompare(a.local_date))
    .slice(0, 40));

const peakHour = computed(() => {
  const top = [...props.hours].sort((a, b) => (b.papers ?? 0) - (a.papers ?? 0))[0];
  return top ? `${String(top.local_hour).padStart(2, '0')}:00` : null;
});
</script>

<template>
    <div class="heatmap-container panel">
        <h4 class="panel-title">Revision calendar</h4>
        <EChart class="panel-chart" :option="heatmapOption" :has-data="hasData" label="revision calendar" />
    </div>
    <div class="session-line-container panel">
        <h4 class="panel-title">Time per paper</h4>
        <EChart class="panel-chart" :option="sessionOption" :has-data="hasData" label="time per paper" />
    </div>
    <div class="session-log panel">
        <h4 class="panel-title">Sessions</h4>
        <div v-if="sessions.length" class="session-scroll">
            <table class="session-table">
                <thead>
                    <tr><th>Date</th><th>Paper</th><th class="num">Score</th></tr>
                </thead>
                <tbody>
                    <tr v-for="s in sessions" :key="s.id">
                        <td>{{ shortDate(s.local_date) }}</td>
                        <td>{{ subjectLabel(s, attempts) }}</td>
                        <td class="num">{{ pct(s.accuracy) ?? '—' }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div v-else class="session-empty">No sessions yet</div>
    </div>
    <div class="quickview-container quickview-container-1">
        <MicroStat label="Current streak" :value="streaks.current ? `${streaks.current}d` : '0d'" hint="consecutive days" />
    </div>
    <div class="quickview-container quickview-container-2">
        <MicroStat label="Longest streak" :value="streaks.longest ? `${streaks.longest}d` : '0d'" hint="personal best" />
    </div>
    <div class="quickview-container quickview-container-3">
        <MicroStat label="Total time" :value="duration(totals.timeMs)" hint="all papers" />
    </div>
    <div class="quickview-container quickview-container-4">
        <MicroStat label="Peak hour" :value="peakHour" :hint="totals.avgPaperMs ? `${duration(totals.avgPaperMs)} avg paper` : 'when you revise'" />
    </div>
</template>

<style lang="scss" scoped>
    // internal layout only - every grid placement below is unchanged.
    .panel { display: flex; flex-direction: column; min-height: 0; padding: 0.85rem 0.9rem 0.7rem; box-sizing: border-box; }
    .panel-title {
        margin: 0 0 0.4rem; font-family: var(--font-body); font-size: 0.72rem; font-weight: 600;
        letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted);
    }
    .panel-chart { flex: 1 1 auto; min-height: 0; }

    // the session log is a table, not a chart - a short list of discrete
    // events reads better as rows than as marks, and it doubles as the table
    // view the light-mode contrast warning obliges the page to provide.
    .session-scroll { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
    .session-table {
        width: 100%; border-collapse: collapse;
        font-family: var(--font-body); font-size: 0.75rem;
        th {
            position: sticky; top: 0; background: var(--secondary-background);
            text-align: left; font-weight: 600; font-size: 0.68rem; letter-spacing: 0.04em;
            text-transform: uppercase; color: var(--muted); padding: 0.3rem 0.4rem;
        }
        td { padding: 0.34rem 0.4rem; border-top: 1px solid var(--border); color: var(--text); }
        .num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; text-align: right; }
        .swatch { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 0.4rem; }
    }
    .session-empty { flex: 1; display: grid; place-items: center; color: var(--muted); font-size: 0.8rem; }

    .heatmap-container {
        grid-column: 7/21;
        grid-row: 9/21;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .session-line-container {
        grid-column: 3/19;
        grid-row: 1/9;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .session-log {
        grid-column: 1/7;
        grid-row: 9/21;
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .quickview-container {
        background-color: $secondary-background;
        border-radius: 20px;
    }
    .quickview-container-1 {
        grid-column: 1/3;
        grid-row: 1/5;
    }
    .quickview-container-2 {
        grid-column: 1/3;
        grid-row: 5/9;
    }
    .quickview-container-3 {
        grid-column: 19/21;
        grid-row: 1/5;
    }
    .quickview-container-4 {
        grid-column: 19/21;
        grid-row: 5/9;
    }
</style>