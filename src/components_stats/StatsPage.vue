<script setup lang="ts">
// ============================================================================
//
// Statistics navigation at three explicit grains: the whole account, one
// subject, and one completed paper attempt. A topic is never presented as an
// account-wide fact; it only appears after a subject has been chosen.
// ============================================================================

import { computed, ref, watch } from 'vue';
import {
  BarChart3,
  BookOpen,
  BrainCircuit,
  ChevronRight,
  CircleAlert,
  FileText,
  Layers3,
  Target,
} from 'lucide-vue-next';
import NextStepsOverall from './NextSteps-Overall.vue';
import ProgressOverall from './Progress-Overall.vue';
import TopicsOverall from './Topics-Overall.vue';
import EngagementOverall from './Engagement-Overall.vue';
import FocusOverall from './Focus-Overall.vue';
import IdeOverall from './Ide-Overall.vue';
import PaperDetail from './PaperDetail.vue';
import RecommendationBanner from './RecommendationBanner.vue';
import { useStats } from '@/lib/stats/useStats';
import { count, pct, shortDate, subjectLabel } from '@/lib/stats/format';
import {
  progressRecommendation,
  queueRecommendation,
  topicRecommendation,
  engagementRecommendation,
  focusRecommendation,
} from '@/lib/stats/recommendations';
import { accuracyTrend as modelAccuracyTrend } from '@/lib/stats/model';

const {
  filter,
  state,
  loading,
  error,
  sectionErrors,
  completedSubjects,
  totals,
  streaks,
  focus,
  topics,
  rankedTopics,
  queue,
  missed,
  readinessByPaper,
  ide,
} = useStats();

type Resolution = 'overall' | 'subject' | 'paper';
const resolution = ref<Resolution>('overall');
const selectedAttemptId = ref<string | null>(null);

const selectedSubjectCode = computed({
  get: () => filter.subjectCodes?.[0] ?? '',
  set: (code: string) => {
    filter.subjectCodes = code ? [code] : undefined;
    selectedAttemptId.value = null;
  },
});

const subjectOptions = computed(() => completedSubjects.value.map(subject => ({
  code: subject.subject_code,
  label: subjectLabel(subject, completedSubjects.value),
})));

const completedAttemptOptions = computed(() => [...state.allAttempts]
  .filter(attempt => !selectedSubjectCode.value || attempt.subject_code === selectedSubjectCode.value)
  .sort((a, b) => (b.finished_at ?? b.started_at).localeCompare(a.finished_at ?? a.started_at)));

const selectedAttempt = computed(() =>
  completedAttemptOptions.value.find(attempt => attempt.id === selectedAttemptId.value) ?? null);

const selectedSubject = computed(() =>
  completedSubjects.value.find(subject => subject.subject_code === selectedSubjectCode.value) ?? null);

const latestAttempt = computed(() => [...state.attempts]
  .sort((a, b) => (b.finished_at ?? b.started_at).localeCompare(a.finished_at ?? a.started_at))[0] ?? null);

const accuracyTrend = computed(() => modelAccuracyTrend(state.attempts));

const daysSinceLast = computed(() => {
  const latest = latestAttempt.value?.local_date;
  if (!latest) return null;
  return Math.max(0, Math.round(
    (Date.now() - new Date(`${latest}T00:00:00`).getTime()) / 86_400_000,
  ));
});

const rankedSubjects = computed(() => [...state.subjects]
  .filter(subject => subject.accuracy !== null)
  .sort((a, b) => (b.accuracy ?? 0) - (a.accuracy ?? 0)));

const asSubject = (subject: (typeof rankedSubjects)['value'][number] | undefined) =>
  subject?.accuracy !== null && subject !== undefined
    ? { name: subjectLabel(subject, completedSubjects.value), accuracy: subject.accuracy }
    : null;

const progressRec = computed(() => progressRecommendation({
  papers: totals.value.papers,
  accuracy: totals.value.accuracy,
  trend: accuracyTrend.value,
  strongest: resolution.value === 'overall' ? asSubject(rankedSubjects.value[0]) : null,
  weakest: resolution.value === 'overall' ? asSubject(rankedSubjects.value[rankedSubjects.value.length - 1]) : null,
  subjectName: resolution.value === 'subject' && selectedSubject.value
    ? subjectLabel(selectedSubject.value, completedSubjects.value)
    : undefined,
}));

const topicRec = computed(() => topicRecommendation({
  topics: topics.value.map(topic => ({
    name: topic.topic_name,
    questions: topic.questions,
    accuracy: topic.accuracy,
  })),
}));

const queueRec = computed(() => queueRecommendation({
  queue: queue.value,
  missed: missed.value.length,
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

const pageSubtitle = computed(() => {
  if (loading.value) return 'Reading your completed attempts…';
  if (resolution.value === 'paper' && selectedAttempt.value) {
    return `${selectedAttempt.value.paper_id} · ${selectedAttempt.value.marks_awarded}/${selectedAttempt.value.marks_total || '—'} marks`;
  }
  if (resolution.value === 'subject' && selectedSubject.value) {
    return `${subjectLabel(selectedSubject.value, completedSubjects.value)} · ${totals.value.papers} completed papers`;
  }
  if (!state.allAttempts.length) return 'Complete a paper and your performance history will appear here.';
  return `${state.allAttempts.length} papers across ${completedSubjects.value.length} subject${completedSubjects.value.length === 1 ? '' : 's'}.`;
});

const summaryMetrics = computed(() => [
  { label: 'Accuracy', value: pct(totals.value.accuracy) ?? '—', hint: `${totals.value.marksAwarded}/${totals.value.marksTotal || '—'} marks` },
  { label: 'Papers', value: count(totals.value.papers) ?? '0', hint: 'completed attempts' },
  { label: 'Questions', value: count(totals.value.questions) ?? '0', hint: 'recorded answers' },
  {
    label: 'Latest paper',
    value: latestAttempt.value?.marks_total
      ? `${latestAttempt.value.marks_awarded}/${latestAttempt.value.marks_total}`
      : '—',
    hint: latestAttempt.value ? shortDate(latestAttempt.value.local_date) : 'no completed paper',
  },
]);

function openSubject(code: string) {
  resolution.value = 'subject';
  selectedSubjectCode.value = code;
}

function setResolution(next: Resolution) {
  resolution.value = next;
  if (next === 'overall') {
    filter.subjectCodes = undefined;
    selectedAttemptId.value = null;
    return;
  }

  if (!selectedSubjectCode.value) {
    const firstSubject = completedSubjects.value[0]?.subject_code;
    if (firstSubject) filter.subjectCodes = [firstSubject];
  }

  selectedAttemptId.value = next === 'paper' ? completedAttemptOptions.value[0]?.id ?? null : null;
}

watch(completedAttemptOptions, options => {
  if (resolution.value !== 'paper') return;
  if (!options.some(attempt => attempt.id === selectedAttemptId.value)) {
    selectedAttemptId.value = options[0]?.id ?? null;
  }
});

function paperOptionLabel(attempt: (typeof completedAttemptOptions)['value'][number]): string {
  const score = attempt.marks_total > 0
    ? `${attempt.marks_awarded}/${attempt.marks_total}`
    : 'unmarked';
  return `${attempt.paper_id} · ${score} · ${shortDate(attempt.local_date)}`;
}
</script>

<template>
  <main class="stats-page">
    <div class="stats-shell">
      <header class="stats-header">
        <div>
          <p class="page-eyebrow"><BarChart3 aria-hidden="true" /> Performance</p>
          <h1>Statistics at the right level.</h1>
          <p class="page-subtitle">{{ pageSubtitle }}</p>
        </div>
        <p v-if="error" class="page-error" role="alert">
          <CircleAlert aria-hidden="true" /> {{ error }}
        </p>
      </header>

      <nav class="resolution-tabs" aria-label="Statistics resolution">
        <button type="button" :class="{ active: resolution === 'overall' }" :aria-pressed="resolution === 'overall'" @click="setResolution('overall')">
          <BarChart3 aria-hidden="true" />
          <span><strong>Overall</strong><small>Account-wide pattern</small></span>
        </button>
        <ChevronRight class="resolution-arrow" aria-hidden="true" />
        <button type="button" :class="{ active: resolution === 'subject' }" :aria-pressed="resolution === 'subject'" @click="setResolution('subject')">
          <BookOpen aria-hidden="true" />
          <span><strong>Subject</strong><small>Topics and subject trend</small></span>
        </button>
        <ChevronRight class="resolution-arrow" aria-hidden="true" />
        <button type="button" :class="{ active: resolution === 'paper' }" :aria-pressed="resolution === 'paper'" @click="setResolution('paper')">
          <FileText aria-hidden="true" />
          <span><strong>Paper</strong><small>Question-by-question evidence</small></span>
        </button>
      </nav>

      <div v-if="resolution !== 'overall'" class="scope-selectors">
        <label>
          <span>Subject</span>
          <select v-model="selectedSubjectCode" :disabled="loading || !subjectOptions.length">
            <option v-if="!subjectOptions.length" value="">No completed subjects</option>
            <option v-for="subject in subjectOptions" :key="subject.code" :value="subject.code">{{ subject.label }}</option>
          </select>
        </label>
        <label v-if="resolution === 'paper'">
          <span>Completed paper</span>
          <select v-model="selectedAttemptId" :disabled="loading || !completedAttemptOptions.length">
            <option v-if="!completedAttemptOptions.length" :value="null">No completed papers</option>
            <option v-for="attempt in completedAttemptOptions" :key="attempt.id" :value="attempt.id">{{ paperOptionLabel(attempt) }}</option>
          </select>
        </label>
      </div>

      <template v-if="resolution !== 'paper'">
        <section class="summary-grid" aria-label="Performance summary">
          <article v-for="metric in summaryMetrics" :key="metric.label">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.hint }}</small>
          </article>
        </section>

        <section v-if="resolution === 'overall'" class="content-section subject-overview" aria-labelledby="subjects-title">
          <div class="section-heading">
            <div class="section-icon"><Layers3 aria-hidden="true" /></div>
            <div><p>Choose a subject to see its topics</p><h2 id="subjects-title">Subject performance</h2></div>
          </div>
          <div v-if="completedSubjects.length" class="subject-grid">
            <button v-for="subject in completedSubjects" :key="subject.subject_code" type="button" @click="openSubject(subject.subject_code)">
              <span class="subject-code">{{ subject.subject_code }}</span>
              <strong>{{ subjectLabel(subject, completedSubjects) }}</strong>
              <span class="subject-score">{{ pct(subject.accuracy) ?? '—' }}</span>
              <small>{{ subject.marks_awarded }}/{{ subject.marks_total }} marks · {{ subject.attempts }} papers</small>
              <ChevronRight aria-hidden="true" />
            </button>
          </div>
          <p v-else class="empty-state">No completed subject data yet.</p>
        </section>

        <section v-if="resolution === 'subject'" class="content-section" aria-labelledby="next-title">
          <div class="section-heading">
            <div class="section-icon"><Target aria-hidden="true" /></div>
            <div><p>Within {{ selectedSubject ? subjectLabel(selectedSubject, completedSubjects) : 'this subject' }}</p><h2 id="next-title">What to work on next</h2></div>
          </div>
          <p v-if="sectionErrors.topics" class="section-error">Recommendations could not load: {{ sectionErrors.topics }}</p>
          <template v-else>
            <RecommendationBanner :recommendation="queueRec" />
            <div class="component-grid"><NextStepsOverall :queue="queue" :missed="missed" :readiness="readinessByPaper" /></div>
          </template>
        </section>

        <section v-if="resolution === 'subject'" class="content-section" aria-labelledby="topics-title">
          <div class="section-heading">
            <div class="section-icon"><Layers3 aria-hidden="true" /></div>
            <div><p>Subject-level evidence only</p><h2 id="topics-title">Topics in {{ selectedSubject ? subjectLabel(selectedSubject, completedSubjects) : 'this subject' }}</h2></div>
          </div>
          <p v-if="sectionErrors.topics" class="section-error">Topics could not load: {{ sectionErrors.topics }}</p>
          <template v-else-if="topics.length">
            <RecommendationBanner :recommendation="topicRec" />
            <div class="component-grid"><TopicsOverall :ranked="rankedTopics" :subjects="state.subjects" /></div>
          </template>
          <p v-else class="empty-state">No topic-tagged questions exist for this subject yet.</p>
        </section>

        <section class="content-section" aria-labelledby="progress-title">
          <div class="section-heading">
            <div class="section-icon"><BarChart3 aria-hidden="true" /></div>
            <div><p>{{ resolution === 'overall' ? 'Across every completed paper' : 'Within this subject' }}</p><h2 id="progress-title">Paper score progression</h2></div>
          </div>
          <p v-if="sectionErrors.progress" class="section-error">Progress could not load: {{ sectionErrors.progress }}</p>
          <template v-else>
            <RecommendationBanner :recommendation="progressRec" />
            <div class="component-grid"><ProgressOverall :attempts="state.attempts" :subjects="state.subjects" :totals="totals" :subject-scoped="resolution === 'subject'" /></div>
          </template>
        </section>

        <section class="content-section" aria-labelledby="focus-title">
          <div class="section-heading">
            <div class="section-icon"><BrainCircuit aria-hidden="true" /></div>
            <div><p>How answers happened</p><h2 id="focus-title">Technique and confidence</h2></div>
          </div>
          <p v-if="sectionErrors.focus" class="section-error">Technique statistics could not load: {{ sectionErrors.focus }}</p>
          <template v-else>
            <RecommendationBanner :recommendation="focusRec" />
            <div class="component-grid component-grid--focus"><FocusOverall :calibration="state.calibration" :flags="state.flags" :focus="focus" :answer-changes="state.answerChanges" /></div>
          </template>
        </section>

        <section v-if="resolution === 'overall' && (ide.submissions || sectionErrors.ide)" class="content-section" aria-labelledby="ide-title">
          <div class="section-heading">
            <div class="section-icon"><BrainCircuit aria-hidden="true" /></div>
            <div><p>All pseudocode submissions</p><h2 id="ide-title">Pseudocode progress</h2></div>
          </div>
          <p v-if="sectionErrors.ide" class="section-error">Pseudocode statistics could not load: {{ sectionErrors.ide }}</p>
          <div v-else class="component-grid"><IdeOverall :reading="ide" :submissions="state.ideSubmissions" /></div>
        </section>

        <section v-if="resolution === 'overall'" class="content-section content-section--secondary" aria-labelledby="habits-title">
          <div class="section-heading">
            <div class="section-icon"><BookOpen aria-hidden="true" /></div>
            <div><p>Supporting context</p><h2 id="habits-title">Study habits</h2></div>
          </div>
          <p v-if="sectionErrors.engagement" class="section-error">Study habits could not load: {{ sectionErrors.engagement }}</p>
          <template v-else>
            <RecommendationBanner :recommendation="engagementRec" />
            <div class="component-grid"><EngagementOverall :attempts="state.attempts" :daily="state.daily" :hours="state.hours" :streaks="streaks" :totals="totals" /></div>
          </template>
        </section>
      </template>

      <section v-else class="paper-resolution" aria-live="polite">
        <p v-if="sectionErrors.focus" class="section-error">Question-level performance could not load: {{ sectionErrors.focus }}</p>
        <PaperDetail
          v-if="selectedAttempt"
          :attempt="selectedAttempt"
          :questions="state.flags"
          :completed-subjects="completedSubjects"
        />
        <div v-else class="empty-paper-state">
          <FileText aria-hidden="true" />
          <h2>No completed paper in this subject</h2>
          <p>Choose another subject or complete a paper to unlock question-level evidence.</p>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped lang="scss">
.stats-page {
  min-height: 100vh;
  padding: clamp(2rem, 4vw, 4.5rem) clamp(1.5rem, 4vw, 4rem) 6rem calc(5vw + clamp(1.5rem, 4vw, 4rem));
  background: var(--background);
  color: var(--text);
}
.stats-shell { width: min(100%, 88rem); margin: 0 auto; }
.stats-header { display: flex; justify-content: space-between; gap: 2rem; align-items: flex-start; }
.page-eyebrow,
.section-heading p {
  display: flex; align-items: center; gap: 0.45rem; margin: 0 0 0.65rem;
  color: var(--accent); font: 600 0.68rem var(--font-mono); letter-spacing: 0.08em; text-transform: uppercase;
}
.page-eyebrow svg { width: 1rem; height: 1rem; }
.stats-header h1 { margin: 0; font: 500 clamp(2.1rem, 4.5vw, 4.25rem)/1.05 var(--font-display); letter-spacing: -0.045em; }
.page-subtitle { margin: 1rem 0 0; color: var(--muted); font-size: 0.92rem; }
.page-error,
.section-error {
  display: flex; align-items: flex-start; gap: 0.5rem; margin: 0; padding: 0.75rem 0.9rem;
  border: 1px solid color-mix(in srgb, var(--danger) 35%, var(--border)); border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--danger) 8%, var(--secondary-background)); color: var(--danger); font-size: 0.78rem;
}
.page-error { max-width: 28rem; }
.page-error svg { width: 1rem; flex: 0 0 auto; }
.resolution-tabs {
  display: grid; grid-template-columns: 1fr auto 1fr auto 1fr; align-items: center; gap: 0.8rem;
  margin-top: 3rem; padding: 0.65rem; border: 1px solid var(--border); border-radius: var(--radius-card);
  background: var(--secondary-background);
}
.resolution-tabs button {
  display: flex; align-items: center; gap: 0.8rem; min-width: 0; padding: 0.9rem 1rem;
  border: 1px solid transparent; border-radius: var(--radius-control); background: transparent;
  color: var(--muted); text-align: left; cursor: pointer;
}
.resolution-tabs button > svg { width: 1.15rem; flex: 0 0 auto; }
.resolution-tabs button span { display: grid; gap: 0.15rem; }
.resolution-tabs strong { color: var(--text); font: 600 0.82rem var(--font-display); }
.resolution-tabs small { font: 0.68rem var(--font-body); }
.resolution-tabs button.active { border-color: var(--accent); background: var(--tertiary-background); color: var(--accent); }
.resolution-arrow { width: 0.9rem; color: var(--muted); opacity: 0.45; }
.scope-selectors { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin-top: 1rem; }
.scope-selectors label { display: grid; gap: 0.4rem; }
.scope-selectors label > span { color: var(--muted); font: 600 0.65rem var(--font-body); text-transform: uppercase; letter-spacing: 0.06em; }
.scope-selectors select {
  width: 100%; padding: 0.8rem 2.5rem 0.8rem 0.9rem; border: 1px solid var(--border);
  border-radius: var(--radius-control); background: var(--secondary-background); color: var(--text); font: 0.8rem var(--font-body);
}
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; margin-top: 2.5rem; }
.summary-grid article {
  display: grid; gap: 0.3rem; min-height: 8rem; align-content: center; padding: 1.1rem 1.25rem;
  border: 1px solid var(--border); border-radius: var(--radius-card); background: var(--secondary-background);
}
.summary-grid span { color: var(--muted); font: 600 0.66rem var(--font-body); text-transform: uppercase; letter-spacing: 0.06em; }
.summary-grid strong { color: var(--text); font: 500 clamp(1.35rem, 2.5vw, 2rem) var(--font-mono); }
.summary-grid small { color: var(--muted); font-size: 0.68rem; }
.content-section,
.paper-resolution { margin-top: clamp(3.5rem, 7vw, 6rem); }
.content-section--secondary { opacity: 0.88; }
.section-heading { display: flex; align-items: flex-start; gap: 0.85rem; margin-bottom: 1.15rem; }
.section-heading p { margin-bottom: 0.35rem; }
.section-heading h2 { margin: 0; font: 500 clamp(1.35rem, 2.5vw, 2rem) var(--font-display); letter-spacing: -0.025em; }
.section-icon {
  display: grid; place-items: center; width: 2.5rem; height: 2.5rem; flex: 0 0 auto;
  border: 1px solid var(--border); border-radius: var(--radius-control); background: var(--secondary-background); color: var(--accent);
}
.section-icon svg { width: 1.05rem; }
.content-section > .recommendation-banner { margin-bottom: 0.9rem; }
.subject-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
.subject-grid button {
  position: relative; display: grid; gap: 0.45rem; min-height: 12rem; padding: 1.25rem;
  border: 1px solid var(--border); border-radius: var(--radius-card); background: var(--secondary-background);
  color: var(--text); text-align: left; cursor: pointer; transition: border-color 160ms ease, transform 160ms ease;
}
.subject-grid button:hover { border-color: var(--accent); transform: translateY(-2px); }
.subject-grid button > svg { position: absolute; top: 1.2rem; right: 1.1rem; width: 1rem; color: var(--accent); }
.subject-code { color: var(--accent); font: 0.68rem var(--font-mono); }
.subject-grid strong { max-width: 80%; font: 600 0.95rem var(--font-display); }
.subject-score { align-self: end; font: 500 2rem var(--font-mono); }
.subject-grid small { color: var(--muted); font-size: 0.68rem; }
.component-grid {
  display: grid; grid-template-columns: repeat(20, minmax(0, 1fr)); grid-template-rows: repeat(20, 46px);
  gap: 1rem; min-height: 920px; padding-top: 1rem;
}
.component-grid--focus { min-height: 1050px; }
.empty-state,
.empty-paper-state { color: var(--muted); font-size: 0.82rem; }
.empty-paper-state {
  display: grid; justify-items: center; gap: 0.5rem; min-height: 22rem; place-content: center;
  border: 1px solid var(--border); border-radius: var(--radius-card); background: var(--secondary-background); text-align: center;
}
.empty-paper-state svg { width: 2rem; color: var(--accent); }
.empty-paper-state h2,
.empty-paper-state p { margin: 0; }
.empty-paper-state h2 { color: var(--text); font-family: var(--font-display); }
button:focus-visible,
select:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 74rem) {
  .subject-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .resolution-tabs small { display: none; }
}
@media (max-width: 58rem) {
  .stats-page { padding-left: calc(5vw + 1.25rem); padding-right: 1.25rem; }
  .resolution-tabs { grid-template-columns: repeat(3, 1fr); }
  .resolution-arrow { display: none; }
  .resolution-tabs button { justify-content: center; text-align: center; }
  .resolution-tabs button > svg { display: none; }
  .scope-selectors { grid-template-columns: 1fr; }
  .subject-grid { grid-template-columns: 1fr; }
}
</style>
