<script setup lang="ts">
import NextStepsOverall from './NextSteps-Overall.vue';
import ProgressOverall from './Progress-Overall.vue';
import TopicsOverall from './Topics-Overall.vue';
import EngagementOverall from './Engagement-Overall.vue';
import FocusOverall from './Focus-Overall.vue';
import IdeOverall from './Ide-Overall.vue';
import CardStrip from './CardStrip.vue';
import Multiselect from '@vueform/multiselect';
import EChart from './EChart.vue';
import RecommendationBanner from './RecommendationBanner.vue';
import { computed, ref } from 'vue';
import { useStats } from '@/lib/stats/useStats';
import { baseTooltip, type ChartTheme } from '@/lib/charts/echarts';
import { pct, subjectLabel } from '@/lib/stats/format';
import {
  progressRecommendation, queueRecommendation, topicRecommendation,
  engagementRecommendation, focusRecommendation,
} from '@/lib/stats/recommendations';
import { accuracyTrend as modelAccuracyTrend } from '@/lib/stats/model';
import type { ExamSeries } from '@/lib/types/enums';

// the filters were ['Wade Cooper', 'Arlene Mccoy', ...] and bound to
// nothing. They now write straight into the query filter, so changing one
// re-reads the page.
const {
  filter, state, loading, error, hasData, totals, streaks, focus, topics,
  rankedTopics, queue, missed, readinessByPaper, ide,
} = useStats();

// Options come from what the user has actually sat - an exam year with no
// attempts behind it is a dead end, and offering it makes the filter feel
// broken.
const yearOptions = computed(() => state.options?.examYears ?? []);

// the series filter listed the raw stored codes - "s" and "w" - which is
// what the database holds and not what anyone calls them.
const SERIES_LABEL: Record<string, string> = {
  s: 'Summer (May/June)', w: 'Winter (Oct/Nov)', m: 'March',
};
const seriesOptions = computed(() =>
  (state.options?.series ?? []).map(code => ({
    value: code, label: SERIES_LABEL[code] ?? code,
  })));

// disambiguated for the same reason as everywhere else - the list showed
// "Computer Science" twice, and picking one of them was a coin flip.
const subjectOptions = computed(() => {
  const codes = state.options?.subjectCodes ?? [];
  const named = codes.map(code => ({
    subject_code: code,
    subject_name: state.options?.subjectNames.get(code) ?? code,
  }));
  return named.map(s => ({ value: s.subject_code, label: subjectLabel(s, named) }));
});

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

// the section chevrons now control their content instead of advertising
// an inert collapse action.
type SectionId = 'nextSteps' | 'topics' | 'progress' | 'ide' | 'focus' | 'engagement';
const collapsedSections = ref<Set<SectionId>>(new Set());

function isExpanded(section: SectionId) {
  return !collapsedSections.value.has(section);
}

function toggleSection(section: SectionId) {
  const next = new Set(collapsedSections.value);
  if (next.has(section)) next.delete(section);
  else next.add(section);
  collapsedSections.value = next;
}

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

// was computed here, and identically in Progress-Overall.vue. Both now
// call the one definition in model.ts - two copies of a claim about the
// student is two chances for the page to contradict itself.
const accuracyTrend = computed(() => modelAccuracyTrend(state.attempts));

const daysSinceLast = computed(() => {
  const latest = state.attempts.reduce<string | null>(
    (m, a) => (m === null || a.local_date > m ? a.local_date : m), null);
  if (!latest) return null;
  return Math.max(0, Math.round(
    (Date.now() - new Date(`${latest}T00:00:00`).getTime()) / 86_400_000));
});

const asSubject = (s: (typeof rankedSubjects)['value'][number] | undefined) =>
  s && s.accuracy != null
    // disambiguated - 0478 and 9618 are both "Computer Science", and the
    // banner previously named the same subject as both strongest and weakest.
    ? { name: subjectLabel(s, state.subjects), accuracy: s.accuracy }
    : null;

const progressRec = computed(() => progressRecommendation({
  papers: totals.value.papers,
  accuracy: totals.value.accuracy,
  trend: accuracyTrend.value,
  strongest: asSubject(rankedSubjects.value[0]),
  weakest: asSubject(rankedSubjects.value[rankedSubjects.value.length - 1]),
}));

// topic mastery reads its own rows rather than the subject rollup - a
// topic is not a subject and the two disagree by design (a question tagged with
// two topics counts its marks toward both, so the topic totals do not sum to
// the paper's). See the header of 00000000000004_question_topics.sql.
const topicRec = computed(() => topicRecommendation({
  topics: topics.value.map(t => ({
    name: t.topic_name, questions: t.questions, accuracy: t.accuracy,
  })),
}));

// the Next steps banner reads the queue, not the topic list - it has to
// name the same item the panel beneath it ranks first, or the section
// contradicts itself in its own header.
const queueRec = computed(() => queueRecommendation({
  queue: queue.value, missed: missed.value.length,
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
        name: subjectLabel(s, state.subjects),
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
        <!-- first, and deliberately. docs/solver/stats_priority.md ranks
             what students act on: recommendations, self-assessment feedback
             and re-practice outrank every backward-looking chart below, and
             time-on-task - which used to lead this page - ranks last of
             fifteen. The one section that ends in a verb goes at the top. -->
        <div v-if="queue.length" class="section-container nextsteps-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-compass-icon lucide-compass"><path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z"/><circle cx="12" cy="12" r="10"/></svg> next steps</h1>
                <!-- collapse button controls the section content below. -->
                <button
                  type="button"
                  class="expand-btn"
                  :class="{ 'is-collapsed': !isExpanded('nextSteps') }"
                  :aria-expanded="isExpanded('nextSteps')"
                  aria-label="Toggle next steps section"
                  @click="toggleSection('nextSteps')"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </button>
            </div>
            <RecommendationBanner v-show="isExpanded('nextSteps')" class="section-rec" :recommendation="queueRec" />
            <div v-show="isExpanded('nextSteps')" class="section-body">
                <NextStepsOverall :queue="queue" :missed="missed" :readiness="readinessByPaper" />
            </div>
        </div>
        <!-- hidden entirely when nothing is tagged, rather than rendered
             empty - docs/stats_page_design.md §6. Topic tagging covers the
             multiple-choice syllabuses only, so a student working through
             9618 sees no section here and that is correct, not broken. -->
        <div v-if="topics.length" class="section-container topics-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-layers-icon lucide-layers"><path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"/><path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12"/><path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17"/></svg> topics</h1>
                <button
                  type="button"
                  class="expand-btn"
                  :class="{ 'is-collapsed': !isExpanded('topics') }"
                  :aria-expanded="isExpanded('topics')"
                  aria-label="Toggle topics section"
                  @click="toggleSection('topics')"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </button>
            </div>
            <RecommendationBanner v-show="isExpanded('topics')" class="section-rec" :recommendation="topicRec" />
            <div v-show="isExpanded('topics')" class="section-body">
                <TopicsOverall :ranked="rankedTopics" :subjects="state.subjects" />
            </div>
        </div>
        <div class="section-container progress-container">
            <div class="section-header">
                <h1 class="section-inner-header progress-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trending-up-down-icon lucide-trending-up-down"><path d="M14.828 14.828 21 21"/><path d="M21 16v5h-5"/><path d="m21 3-9 9-4-4-6 6"/><path d="M21 8V3h-5"/></svg> progress</h1>
                <button
                  type="button"
                  class="expand-btn"
                  :class="{ 'is-collapsed': !isExpanded('progress') }"
                  :aria-expanded="isExpanded('progress')"
                  aria-label="Toggle progress section"
                  @click="toggleSection('progress')"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </button>
            </div>
            <RecommendationBanner v-show="isExpanded('progress')" class="section-rec" :recommendation="progressRec" />
            <div v-show="isExpanded('progress')" class="section-body">
                <ProgressOverall :attempts="state.attempts" :subjects="state.subjects" :totals="totals" />
            </div>
        </div>
        <!-- hidden entirely for a student who has never submitted
             pseudocode, on the same rule as Topics above - an empty section
             says "this feature is broken", an absent one says nothing. The
             IDE is a separate app for most of this page's readers, and the
             heading names it so the figures below cannot be mistaken for the
             solver's. -->
        <div v-if="ide.submissions" class="section-container ide-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-code-icon lucide-code"><path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/></svg> pseudocode</h1>
                <button
                  type="button"
                  class="expand-btn"
                  :class="{ 'is-collapsed': !isExpanded('ide') }"
                  :aria-expanded="isExpanded('ide')"
                  aria-label="Toggle pseudocode section"
                  @click="toggleSection('ide')"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </button>
            </div>
            <div v-show="isExpanded('ide')" class="section-body">
                <IdeOverall :reading="ide" :submissions="state.ideSubmissions" />
            </div>
        </div>
        <div class="section-container focus-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-crosshair-icon lucide-crosshair"><circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/></svg> focuses</h1>
                <button
                  type="button"
                  class="expand-btn"
                  :class="{ 'is-collapsed': !isExpanded('focus') }"
                  :aria-expanded="isExpanded('focus')"
                  aria-label="Toggle focuses section"
                  @click="toggleSection('focus')"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </button>
            </div>
            <RecommendationBanner v-show="isExpanded('focus')" class="section-rec" :recommendation="focusRec" />
            <div v-show="isExpanded('focus')" class="section-body">
                <FocusOverall :calibration="state.calibration" :flags="state.flags" :focus="focus" :answer-changes="state.answerChanges" />
            </div>
        </div>
        <div class="section-container engagement-container">
            <div class="section-header">
                <h1 class="section-inner-header"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-activity-icon lucide-activity"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg> engagement</h1>
                <button
                  type="button"
                  class="expand-btn"
                  :class="{ 'is-collapsed': !isExpanded('engagement') }"
                  :aria-expanded="isExpanded('engagement')"
                  aria-label="Toggle engagement section"
                  @click="toggleSection('engagement')"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down-icon lucide-chevron-down"><path d="m6 9 6 6 6-6"/></svg>
                </button>
            </div>
            <RecommendationBanner v-show="isExpanded('engagement')" class="section-rec" :recommendation="engagementRec" />
            <div v-show="isExpanded('engagement')" class="section-body">
                <EngagementOverall :attempts="state.attempts" :daily="state.daily" :hours="state.hours" :streaks="streaks" :totals="totals" />
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
        /* the legend sits to the right of the donut, so the box has to be
           wide enough for both. At 240px the legend was drawn over the chart. */
        min-width: 420px;
        min-height: 200px;
        max-height: 260px;
        align-self: center;
    }

.flex-container {
  display: flex;
  padding: 10px;
  column-gap: 10px;

  .multiselect {
    /* Vue 3's functional :deep() syntax replaces deprecated ::v-deep
       combinators for the third-party multiselect internals below. */
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
        :deep(.multiselect-search) {
            background-color: $tertiary-background;
        }
    }

    :deep(.multiselect-search) {
        transition: background 1s ease;
        background: $secondary-background;
        font-family: 'Lexend';
        color: $text;
    }
    :deep(.multiselect-placeholder) {
        font-family: 'Lexend';
    }
    :deep(.multiselect-dropdown) {
        background-color: $tertiary-background;
        border: none;
    }
    :deep(.multiselect-option) {
        background-color: $tertiary-background;
        color: $text;
        font-family: 'Lexend';
    }
    :deep(.multiselect-option.is-pointed) {
      background-color: $secondary-background;
      color: white !important;
    }

    :deep(.multiselect-no-results) {
      font-family: 'Lexend';
      color: $text !important;
    }

    :deep(.multiselect-single-label) {
        font-family: 'Lexend';
    }

    :deep(.multiselect-clear .multiselect-clear-icon) {
        &:hover {
            background-color: white !important;
        }
    }
  }
}

.grid-container {
    width: 100%;
    padding-left: 5vw;
    display: grid;
    grid-template-columns: repeat(20, 1fr);
    /* was `height: 400%` with `repeat(40, 1fr)`. 1fr divides whatever height
       the container happens to have, and 400% resolved to 8860px - so every row
       became 221px regardless of what sat in it, the page ran to 8860px, and the
       header alone was 1551px tall for a title and three dropdowns.
       An explicit row height makes the grid additive: 40 rows of 90px is a
       2,880px page, and every span below keeps the proportions it was drawn
       with. */
    /* the first ten rows are fixed - they hold the marquee, a gap and the
       header, all of which have a known size. The three sections that follow
       are `auto`, because their height is a function of their content and
       pinning them to ten 90px rows each made the Focus section overflow its
       box and draw on top of Engagement's calendar. A section that needs
       1,050px now gets 1,050px. */
    /* five `auto` rows - Next steps and Topics joined the original three. */
    grid-template-rows: repeat(10, 90px) auto auto auto auto auto;
    background-color: $background;
    /* Nothing here should ever scroll the page sideways. */
    overflow-x: hidden;
}
.top-card-strip-container {
    grid-column: 1/21;
    /* one 90px row clipped the cards, which are ~200px tall - they were cut
       off top and bottom. Two rows fits a card. */
    grid-row: 1/3;
    /* the marquee inside is deliberately wider than this box. Without this
       it escaped and gave the whole page 5,500px of horizontal scroll. */
    overflow: hidden;
}
.header-container {
    grid-column: 1/21;
    /* six rows rather than seven. The block holds a title, one line of
       subtitle, three filters and a 260px donut; the extra row was empty space
       between the card strip and the heading. */
    grid-row: 4/10;
    display: flex;
    align-items: center;
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
/* order follows docs/solver/stats_priority.md SS2 - what a student acts
   on first, not what got built first. Engagement moved from second to last
   because it is carried by time-on-task, which the one ranked study of
   student preferences puts at the bottom of fifteen features.
   The TEMPLATE is in this order too: placing sections by grid-row alone would
   leave the DOM - and so the tab order and every screen reader - disagreeing
   with what the page looks like. */
.focus-container {
    grid-column: 1/21;
    grid-row: 15/16;
}
.engagement-container {
    grid-column: 1/21;
    grid-row: 16/17;
}
/* between Progress and Focus. Backward-looking like Progress, so it does
   not belong above it; ahead of Focus and Engagement because "how is my
   pseudocode going" is a subject question and those two are study-habit
   questions - stats_priority.md SS2 ranks subject outcomes above habits. */
.ide-container {
    grid-column: 1/21;
    grid-row: 14/15;
}
/* Each of these rows is `auto`, so a hidden section collapses to nothing
   rather than leaving a gap where it would have been. */
.nextsteps-container {
    grid-column: 1/21;
    grid-row: 11/12;
}
.topics-container {
    grid-column: 1/21;
    grid-row: 12/13;
}
.progress-container {
    grid-column: 1/21;
    grid-row: 13/14;
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
            /* real button reset plus a visible collapsed state. */
            margin-left: auto;
            color: $accent;
            padding: 0.4rem;
            border: 0;
            background: transparent;
            cursor: pointer;
            line-height: 0;

            svg { transition: transform 0.2s ease; }
            &.is-collapsed svg { transform: rotate(-90deg); }
        }
    }
    .section-body {
        width: 100%;
        display: grid;
        grid-template-columns: repeat(20, 1fr);
        /* was `height: 100%` + `repeat(20, 1fr)`, which divided whatever
           height the section had been given. With the section now sized by its
           content that would collapse to nothing, so the row is explicit: 20
           rows of 46px is the ~920px these grids were drawn against. Sections
           whose body is not a grid (Focus uses flex) simply ignore it. */
        grid-template-rows: repeat(20, 46px);
        padding: 1rem;
        gap: 1rem;
    }
}
</style>
