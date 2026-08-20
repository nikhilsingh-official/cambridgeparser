<script setup lang="ts">
import ProgressOverall from './Progress-Overall.vue';
import EngagementOverall from './Engagement-Overall.vue';
import FocusOverall from './Focus-Overall.vue';
import CardStrip from './CardStrip.vue';
import Multiselect from '@vueform/multiselect';
import EChart from './EChart.vue';
import RecommendationBanner from './RecommendationBanner.vue';
import { computed } from 'vue';
import { useStats } from '@/lib/stats/useStats';
import { baseTooltip, type ChartTheme } from '@/lib/charts/echarts';
import { pct } from '@/lib/stats/format';
import {
  progressRecommendation, engagementRecommendation, focusRecommendation,
} from '@/lib/stats/recommendations';
import type { ExamSeries } from '@/lib/types/enums';

// the filters were ['Wade Cooper', 'Arlene Mccoy', ...] and bound to
// nothing. They now write straight into the query filter, so changing one
// re-reads the page.
const { filter, state, loading, error, hasData, totals, streaks, focus } = useStats();

// Options come from what the user has actually sat - an exam year with no
// attempts behind it is a dead end, and offering it makes the filter feel
// broken.
const yearOptions = computed(() => state.options?.examYears ?? []);
const seriesOptions = computed(() => state.options?.series ?? []);
const subjectOptions = computed(() =>
  (state.options?.subjectCodes ?? []).map(code => ({
    value: code,
    label: state.options?.subjectNames.get(code) ?? code,
  })));

// Multiselect binds v-model directly; writing through computed setters keeps
// `filter` the single source of truth rather than mirroring state into refs
// that then have to be kept in step.
const selectedSubjects = computed({
  get: () => filter.subjectCodes ?? [],
  set: v => { filter.subjectCodes = v.length ? v : undefined; },
});
const selectedYears = computed({
  get: () => filter.examYears ?? [],
  set: v => { filter.examYears = v.length ? v : undefined; },
});
const selectedSeries = computed({
  get: () => filter.series ?? [],
  set: v => { filter.series = v.length ? (v as ExamSeries[]) : undefined; },
});

// the three section readings.
//
// Computed here rather than inside each section component because this is where
// the data already is, and because the banners render in the section HEADERS -
// outside the 20x20 grids the sections own, so adding them costs no chart a row
// and needs no change to layout the author wrote.
//
// Rules, not a model: see the header of lib/stats/recommendations.ts.
const rankedSubjects = computed(() =>
  [...state.subjects].filter(s => s.accuracy != null).sort((a, b) => (b.accuracy ?? 0) - (a.accuracy ?? 0)));

const accuracyTrend = computed(() => {
  const chron = [...state.attempts]
    .filter(a => a.accuracy != null)
    .sort((a, b) => a.local_date.localeCompare(b.local_date));
  if (chron.length < 6) return null;
  const take = Math.min(5, Math.floor(chron.length / 2));
  const mean = (xs: typeof chron) => xs.reduce((n, a) => n + (a.accuracy ?? 0), 0) / xs.length;
  return mean(chron.slice(-take)) - mean(chron.slice(0, take));
});

const daysSinceLast = computed(() => {
  const latest = state.attempts.reduce<string | null>(
    (m, a) => (m === null || a.local_date > m ? a.local_date : m), null);
  if (!latest) return null;
  return Math.max(0, Math.round(
    (Date.now() - new Date(`${latest}T00:00:00`).getTime()) / 86_400_000));
});

const asSubject = (s: (typeof rankedSubjects)['value'][number] | undefined) =>
  s && s.accuracy != null
    ? { name: s.subject_name ?? s.subject_code, accuracy: s.accuracy }
    : null;

const progressRec = computed(() => progressRecommendation({
  papers: totals.value.papers,
  accuracy: totals.value.accuracy,
  trend: accuracyTrend.value,
  strongest: asSubject(rankedSubjects.value[0]),
  weakest: asSubject(rankedSubjects.value[rankedSubjects.value.length - 1]),
}));

const engagementRec = computed(() => engagementRecommendation({
  papers: totals.value.papers,
  currentStreak: streaks.value.current,
  longestStreak: streaks.value.longest,
  daysSinceLast: daysSinceLast.value,
  avgPaperMs: totals.value.avgPaperMs,
}));

const focusRec = computed(() => focusRecommendation({
  questions: focus.value.questions,
  overconfident: focus.value.overconfident,
  underconfident: focus.value.underconfident,
  guesses: focus.value.guesses,
  guessAccuracy: focus.value.guessAccuracy,
  answerChanges: state.answerChanges,
}));

const subtitle = computed(() => {
  if (loading.value) return 'Reading your attempt history…';
  if (error.value) return 'Could not load your statistics.';
  if (!hasData.value) return 'No completed papers yet. Sit one and this page fills in.';
  const acc = pct(totals.value.accuracy) ?? '—';
  return `${totals.value.papers} papers · ${totals.value.questions} questions · ${acc} overall accuracy.`;
});

// The header pie: how the marks split across subjects. Categorical, fixed
// order, capped at six - past six slots the palette stops being separable and
// the answer belongs in the subject table instead.
const subjectSplitOption = (theme: ChartTheme) => ({
  tooltip: {
    ...baseTooltip(theme), trigger: 'item',
    formatter: (p: { name: string; value: number; percent: number }) =>
      `${p.name}<br/>${p.value} marks · ${p.percent}%`,
  },
  legend: {
    orient: 'vertical', right: 0, top: 'middle', icon: 'circle',
    itemWidth: 8, itemHeight: 8,
    textStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 11 },
  },
  series: [{
    type: 'pie',
    radius: ['52%', '76%'],
    center: ['32%', '50%'],
    itemStyle: { borderColor: theme.surface, borderWidth: 2, borderRadius: 3 },
    label: { show: false },
    labelLine: { show: false },
    data: [...state.subjects]
      .sort((a, b) => (b.marks_awarded ?? 0) - (a.marks_awarded ?? 0))
      .slice(0, 6)
      .map((s, i) => ({
        name: s.subject_name ?? s.subject_code,
        value: s.marks_awarded ?? 0,
        itemStyle: { color: theme.series[i] },
      })),
  }],
});
</script>
<template>
    <div class="grid-container">
        <div class="top-card-strip-container">
            <CardStrip
              :bottom="false"
              :attempts="state.attempts"
              :subjects="state.subjects"
              :streaks="streaks"
              :totals="totals" />
        </div>
        <!--<div class="questions-list-container">
            <QuestionsList></QuestionsList>
        </div>-->
        <div class="header-container">
            <div class="text-container">
                <div class="header-box">
                    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-bar-chart-2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                    <h1>Statistics</h1>
                </div>
                <p class="subtext">{{ subtitle }}</p>
                <p v-if="error" class="stats-error" role="alert">{{ error }}</p>
                <div class="flex-container">
                    <Multiselect
                      v-model="selectedSubjects"
                      :options="subjectOptions"
                      mode="multiple"
                      :searchable="true"
                      placeholder="Subjects..."
                    />
                    <Multiselect
                      v-model="selectedYears"
                      :options="yearOptions"
                      mode="multiple"
                      :searchable="true"
                      placeholder="Years..."
                    />
                    <Multiselect
                      v-model="selectedSeries"
                      :options="seriesOptions"
                      mode="multiple"
                      :searchable="true"
                      placeholder="Series..."
                    />
                </div>
            </div>
            <div class="pie-container">
                <EChart :option="subjectSplitOption" :has-data="hasData" label="marks by subject" />
            </div>
        </div>
        <div class="section-container progress-container">
            <div class="section-header">
                <h1 class="section-inner-header progress-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trending-up-down-icon lucide-trending-up-down"><path d="M14.828 14.828 21 21"/><path d="M21 16v5h-5"/><path d="m21 3-9 9-4-4-6 6"/><path d="M21 8V3h-5"/></svg> progress</h1>
                <div class="expand-btn">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </div>
            </div>
            <RecommendationBanner class="section-rec" :recommendation="progressRec" />
            <div class="section-body">
                <ProgressOverall :attempts="state.attempts" :subjects="state.subjects" :totals="totals" />
            </div>
        </div>
        <div class="section-container engagement-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-activity-icon lucide-activity"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg> engagement</h1>
                <div class="expand-btn">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </div>
            </div>
            <RecommendationBanner class="section-rec" :recommendation="engagementRec" />
            <div class="section-body">
                <EngagementOverall :attempts="state.attempts" :daily="state.daily" :hours="state.hours" :streaks="streaks" :totals="totals" />
            </div>
        </div>
        <div class="section-container focus-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-crosshair-icon lucide-crosshair"><circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/></svg> focuses</h1>
                <div class="expand-btn">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </div>
            </div>
            <RecommendationBanner class="section-rec" :recommendation="focusRec" />
            <div class="section-body">
                <FocusOverall :calibration="state.calibration" :flags="state.flags" :focus="focus" :answer-changes="state.answerChanges" />
            </div>
        </div>
    </div>
</template>
<style lang="scss" scoped>
    .stats-error { margin: 0.25rem 0 0; color: var(--danger); font-family: var(--font-body); font-size: 0.8rem; }
    // the chart host fills its container, and this grid cell is large, so
    // an unconstrained pie rendered several hundred pixels across and dwarfed
    // the header text beside it. Bound it.
    // the section banners sit between each section's header and its grid,
    // so they introduce the charts without taking a row from them.
    .section-rec { margin: 0 0 0.75rem; }

    .pie-container {
        min-height: 180px;
        max-height: 240px;
        align-self: center;
    }

.flex-container {
  display: flex;
  padding: 10px;
  column-gap: 10px;

  .multiselect {
    background: $secondary-background;
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 0.9rem;
    color: $text;
    border: none;
    outline: none;
    transition: background 1s ease;

    &:hover {
        background-color: $tertiary-background;
        ::v-deep .multiselect-search {
            background-color: $tertiary-background;
        }
    }

    ::v-deep .multiselect-search {
        transition: background 1s ease;
        background: $secondary-background;
        font-family: 'Lexend';
        color: $text;
    }
    ::v-deep .multiselect-placeholder {
        font-family: 'Lexend';
    }
    ::v-deep .multiselect-dropdown {
        background-color: $tertiary-background;
        border: none;
    }
    ::v-deep .multiselect-option {
        background-color: $tertiary-background;
        color: $text;
        font-family: 'Lexend';
    }
    ::v-deep .multiselect-option.is-pointed {
      background-color: $secondary-background;
      color: white !important;
    }

    ::v-deep .multiselect-no-results {
      font-family: 'Lexend';
      color: $text !important;
    }

    ::v-deep .multiselect-single-label {
        font-family: 'Lexend';
    }

    ::v-deep .multiselect-clear .multiselect-clear-icon {
        &:hover {
            background-color: white !important;
        }
    }
  }
}

.grid-container {
    width: 100%;
    height: 400%;
    padding-left: 5vw;
    display: grid;
    grid-template-columns: repeat(20, 1fr);
    grid-template-rows: repeat(40, 1fr);
    background-color: $background;
}
.top-card-strip-container {
    grid-column: 1/21;
    grid-row: 1/2;
}
.header-container {
    grid-column: 1/21;
    grid-row: 3/10;
    display: flex;
    .text-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 4rem;
        .header-box {
            font-size: 50px;
            font-family: 'Inter';
            display: flex;
            align-items: center;
            column-gap: 10px;
            color: $text;
            svg {
                color: $accent;
            }
        }
        .subtext {
            color: $text;
            font-family: 'Lexend';
            font-size: 15px;
        }
    }
    // the section banners sit between each section's header and its grid,
    // so they introduce the charts without taking a row from them.
    .pie-container {
        height: 100%;
        aspect-ratio: 1/1;
        background-color: $secondary-background;
        margin-right: 4rem;
        border-radius: 20px;
    }
}
.focus-container {
    grid-column: 1/21;
    grid-row: 31/41;
}
.engagement-container {
    grid-column: 1/21;
    grid-row: 21/31;
}
.progress-container {
    grid-column: 1/21;
    grid-row: 11/21;
}
.section-container {
    display: flex;
    flex-direction: column;
    margin: 0 4rem;
    .section-header {
        width: 100%;
        display: flex;
        align-items: center;
        color: $text;
        padding: 2.5rem 3rem;
        cursor: pointer;
        .section-inner-header {
            display: flex;
            align-items: center;
            column-gap: 20px;
            font-family: 'Inter';
            font-weight: 400;
            margin-right: auto;
            svg {
                color: $accent;
            }
        }
        .progress-header {
            svg {
                margin-top: 10px;
            }
        }
        .expand-btn {
            margin-left: auto;
            color: $accent;
        }
    }
    .section-body {
        width: 100%;
        height: 100%;
        display: grid;
        grid-template-columns: repeat(20, 1fr);
        grid-template-rows: repeat(20, 1fr);
        padding: 1rem;
        gap: 1rem;
    }
}
</style>