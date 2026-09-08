<script setup lang="ts">
// ============================================================================
//
// One completed solver attempt at question resolution. It deliberately shows
// raw evidence (outcome, topics, time and confidence) rather than rolling the
// paper into another opaque score.
// ============================================================================

import { computed, ref, watch } from 'vue';
import { Check, CircleHelp, Clock3, FileQuestion, Target, X } from 'lucide-vue-next';
import type { AttemptSummaryView, QuestionFlagsView } from '@/lib/types/database';
import {
  fetchPaperQuestionAnswers,
  fetchPaperQuestionTopics,
  type PaperQuestionAnswer,
  type PaperQuestionTopic,
} from '@/lib/supabase/queries';
import { duration, pct, shortDate, subjectLabel } from '@/lib/stats/format';
import { readiness } from '@/lib/stats/model';
import { supabase } from '@/stores/useAuth';

const props = defineProps<{
  attempt: AttemptSummaryView;
  questions: QuestionFlagsView[];
  completedSubjects: Array<{ subject_code: string; subject_name?: string | null }>;
}>();

type QuestionOutcome = 'incorrect' | 'correct' | 'unanswered' | 'unmarked';
type OutcomeFilter = 'all' | QuestionOutcome;
const outcomeFilter = ref<OutcomeFilter>('all');
const topics = ref<PaperQuestionTopic[]>([]);
const answers = ref<PaperQuestionAnswer[]>([]);
const topicsLoading = ref(false);
const answersLoading = ref(false);
const topicError = ref(false);
const answerError = ref(false);
let detailGeneration = 0;

watch(
  () => [props.attempt.id, props.attempt.paper_id] as const,
  async ([attemptId, paperId]) => {
    outcomeFilter.value = 'all';
    const generation = ++detailGeneration;
    topics.value = [];
    answers.value = [];
    topicError.value = false;
    answerError.value = false;
    topicsLoading.value = true;
    answersLoading.value = true;

    const [topicResult, answerResult] = await Promise.allSettled([
      fetchPaperQuestionTopics(supabase, paperId),
      fetchPaperQuestionAnswers(supabase, attemptId),
    ]);
    if (generation !== detailGeneration) return;

    if (topicResult.status === 'fulfilled') topics.value = topicResult.value;
    else topicError.value = true;
    if (answerResult.status === 'fulfilled') answers.value = answerResult.value;
    else answerError.value = true;
    topicsLoading.value = false;
    answersLoading.value = false;
  },
  { immediate: true },
);

const paperReadiness = computed(() => readiness(
  props.attempt.marks_awarded,
  props.attempt.marks_total,
  props.attempt.questions_recorded,
  props.attempt.subject_code,
  props.attempt.paper_number,
  props.attempt.paper_id,
));

const topicNames = computed(() => {
  const names = new Map<number, string[]>();
  for (const topic of topics.value) {
    const existing = names.get(topic.questionNumber) ?? [];
    existing.push(topic.topicName);
    names.set(topic.questionNumber, existing);
  }
  return names;
});

const paperQuestions = computed(() => props.questions
  .filter(question => question.exam_attempt_id === props.attempt.id)
  .sort((a, b) => a.question_number - b.question_number));

const selectedOptions = computed(() => new Map(
  answers.value.map(answer => [answer.questionAttemptId, answer.selectedOption]),
));

function questionOutcome(question: QuestionFlagsView): QuestionOutcome {
  if (question.is_correct === true) return 'correct';
  if (question.is_correct === false) return 'incorrect';
  return selectedOptions.value.get(question.question_attempt_id) === null
    ? 'unanswered'
    : 'unmarked';
}

const questionRows = computed(() => paperQuestions.value.map(question => {
  const outcome = questionOutcome(question);
  const option = selectedOptions.value.get(question.question_attempt_id);
  return {
    question,
    outcome,
    selectedOptionLabel: typeof option === 'number' ? String.fromCharCode(65 + option) : null,
  };
}));

const visibleQuestionRows = computed(() => questionRows.value.filter(row =>
  outcomeFilter.value === 'all' || row.outcome === outcomeFilter.value));

const outcomeCounts = computed(() => questionRows.value.reduce(
  (counts, row) => {
    counts.all += 1;
    counts[row.outcome] += 1;
    return counts;
  },
  { all: 0, correct: 0, incorrect: 0, unanswered: 0, unmarked: 0 },
));

const subjectName = computed(() => subjectLabel(props.attempt, props.completedSubjects));

function outcomeLabel(outcome: QuestionOutcome): string {
  const labels: Record<QuestionOutcome, string> = {
    correct: 'Correct',
    incorrect: 'Incorrect',
    unanswered: 'No answer',
    unmarked: 'Unmarked',
  };
  return labels[outcome];
}
</script>

<template>
  <article class="paper-detail">
    <header class="paper-heading">
      <div>
        <p class="eyebrow">{{ subjectName }} · {{ shortDate(attempt.local_date) }}</p>
        <h2>{{ attempt.paper_id }}</h2>
        <p>
          This is one completed attempt. Every figure below belongs to this
          paper rather than an average across a subject.
        </p>
      </div>
      <div class="paper-score">
        <span>{{ attempt.marks_awarded }}/{{ attempt.marks_total || '—' }}</span>
        <small>{{ pct(attempt.accuracy) ?? 'Not marked' }}</small>
      </div>
    </header>

    <div class="paper-metrics">
      <div>
        <FileQuestion aria-hidden="true" />
        <span>Questions</span>
        <strong>{{ attempt.questions_answered }}/{{ attempt.questions_recorded }}</strong>
        <small>answered / recorded</small>
      </div>
      <div>
        <Target aria-hidden="true" />
        <span>Paper grade</span>
        <strong>{{ paperReadiness.reliable ? paperReadiness.grade : '—' }}</strong>
        <small>
          {{ paperReadiness.thresholds
            ? paperReadiness.basis === 'session' ? 'this paper’s published boundary' : 'average component boundary'
            : 'no published boundary' }}
        </small>
      </div>
      <div>
        <Clock3 aria-hidden="true" />
        <span>Time</span>
        <strong>{{ duration(attempt.duration_ms) ?? '—' }}</strong>
        <small>{{ duration(attempt.avg_time_per_question_ms) ?? '—' }} per question</small>
      </div>
    </div>

    <section class="question-section" aria-labelledby="paper-questions-title">
      <div class="question-header">
        <div>
          <p class="eyebrow">Question evidence</p>
          <h3 id="paper-questions-title">Where the marks went</h3>
        </div>
        <div class="outcome-filters" aria-label="Filter questions by outcome">
          <button
            v-for="option in (['all', 'incorrect', 'correct', 'unanswered', 'unmarked'] as OutcomeFilter[])"
            :key="option"
            type="button"
            :class="{ active: outcomeFilter === option }"
            :aria-pressed="outcomeFilter === option"
            @click="outcomeFilter = option"
          >
            {{ option === 'unanswered' ? 'No answer' : option }}
            <span>{{ outcomeCounts[option] }}</span>
          </button>
        </div>
      </div>

      <p v-if="topicError" class="detail-error" role="status">
        Topic labels could not load. Question performance is still available.
      </p>
      <p v-if="answerError" class="detail-error" role="status">
        Answer state could not load. Unmarked answers are not counted as blanks.
      </p>
      <p v-else-if="answersLoading" class="detail-loading" role="status">
        Distinguishing blank and unmarked answers…
      </p>

      <div v-if="paperQuestions.length" class="question-table" role="table" aria-label="Question performance">
        <div class="question-table-head" role="row">
          <span role="columnheader">Question</span>
          <span role="columnheader">Topic</span>
          <span role="columnheader">Result</span>
          <span role="columnheader">Time</span>
          <span role="columnheader">Confidence</span>
        </div>
        <div v-for="row in visibleQuestionRows" :key="row.question.question_attempt_id" class="question-row" role="row">
          <strong role="cell">Q{{ row.question.question_number }}</strong>
          <div class="topic-list" role="cell">
            <span v-if="topicsLoading" class="muted">Loading topics…</span>
            <template v-else-if="topicNames.get(row.question.question_number)?.length">
              <span v-for="topic in topicNames.get(row.question.question_number)" :key="topic">{{ topic }}</span>
            </template>
            <span v-else class="muted">No topic tag</span>
          </div>
          <span
            role="cell"
            class="outcome"
            :class="{
              correct: row.outcome === 'correct',
              incorrect: row.outcome === 'incorrect',
              unanswered: row.outcome === 'unanswered',
              unmarked: row.outcome === 'unmarked',
            }"
          >
            <Check v-if="row.outcome === 'correct'" aria-hidden="true" />
            <X v-else-if="row.outcome === 'incorrect'" aria-hidden="true" />
            <CircleHelp v-else aria-hidden="true" />
            {{ outcomeLabel(row.outcome) }}
            <small v-if="row.selectedOptionLabel">· {{ row.selectedOptionLabel }} selected</small>
          </span>
          <span role="cell" class="tabular">{{ duration(row.question.time_spent_ms) ?? '—' }}</span>
          <span role="cell" class="tabular">{{ pct(row.question.confidence) ?? '—' }}</span>
        </div>
        <p v-if="visibleQuestionRows.length === 0" class="empty-filter">
          No questions match this outcome.
        </p>
      </div>
      <p v-else class="empty-paper">
        Per-question rows are unavailable for this attempt. Its paper-level score is still shown above.
      </p>
    </section>
  </article>
</template>

<style scoped lang="scss">
.paper-detail {
  display: grid;
  gap: 1.25rem;
}

.paper-heading,
.question-section,
.paper-metrics > div {
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--secondary-background);
}

.paper-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 2rem;
  padding: clamp(1.4rem, 3vw, 2.2rem);
}

.eyebrow {
  margin: 0 0 0.55rem;
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.paper-heading h2,
.question-header h3 {
  margin: 0;
  color: var(--text);
  font-family: var(--font-display);
}

.paper-heading h2 { font-size: clamp(1.45rem, 3vw, 2.25rem); }
.paper-heading p:last-child {
  max-width: 60ch;
  margin: 0.65rem 0 0;
  color: var(--muted);
  font-size: 0.85rem;
  line-height: 1.6;
}

.paper-score {
  display: grid;
  flex: 0 0 auto;
  justify-items: end;
  color: var(--text);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.paper-score span { font-size: clamp(1.8rem, 4vw, 3rem); }
.paper-score small { color: var(--muted); }

.paper-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

.paper-metrics > div {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.2rem 0.75rem;
  align-items: center;
  padding: 1.15rem 1.25rem;
}

.paper-metrics svg { grid-row: 1 / 4; width: 1.25rem; color: var(--accent); }
.paper-metrics span,
.paper-metrics small { color: var(--muted); font-size: 0.68rem; }
.paper-metrics strong { color: var(--text); font-family: var(--font-mono); font-size: 1.2rem; }

.question-section { padding: clamp(1.25rem, 3vw, 2rem); }
.question-header { display: flex; justify-content: space-between; gap: 1rem; align-items: end; }
.question-header h3 { font-size: 1.35rem; }

.outcome-filters { display: flex; flex-wrap: wrap; gap: 0.45rem; justify-content: flex-end; }
.outcome-filters button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  background: var(--tertiary-background);
  color: var(--muted);
  font: 600 0.68rem var(--font-body);
  text-transform: capitalize;
  cursor: pointer;
}
.outcome-filters button.active { border-color: var(--accent); color: var(--text); }
.outcome-filters button span { font-family: var(--font-mono); color: var(--accent); }

.detail-error,
.detail-loading,
.empty-filter,
.empty-paper {
  margin: 1rem 0 0;
  color: var(--muted);
  font-size: 0.8rem;
}
.detail-error { color: var(--warning); }

.question-table { margin-top: 1.35rem; border-top: 1px solid var(--border); }
.question-table-head,
.question-row {
  display: grid;
  grid-template-columns: 0.55fr 2fr 0.85fr 0.65fr 0.75fr;
  gap: 1rem;
  align-items: center;
}
.question-table-head {
  padding: 0.75rem 0.85rem;
  color: var(--muted);
  font: 600 0.64rem var(--font-body);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.question-row {
  min-height: 4.1rem;
  padding: 0.7rem 0.85rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.76rem;
}
.question-row > strong { color: var(--text); font-family: var(--font-mono); }
.topic-list { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.topic-list > span:not(.muted) {
  padding: 0.25rem 0.45rem;
  border-radius: var(--radius-control);
  background: var(--tertiary-background);
  color: var(--text);
  font-size: 0.67rem;
}
.muted { color: var(--muted); }
.outcome { display: inline-flex; align-items: center; gap: 0.35rem; width: max-content; }
.outcome svg { width: 0.9rem; height: 0.9rem; }
.outcome.correct { color: var(--success); }
.outcome.incorrect { color: var(--danger); }
.outcome.unanswered { color: var(--muted); }
.outcome.unmarked { color: var(--warning); }
.outcome small { color: inherit; font-size: 0.62rem; }
.tabular { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

@media (max-width: 70rem) {
  .paper-metrics { grid-template-columns: 1fr; }
  .question-header { align-items: flex-start; flex-direction: column; }
  .outcome-filters { justify-content: flex-start; }
  .question-table-head { display: none; }
  .question-row {
    grid-template-columns: 0.5fr 1.5fr 1fr;
  }
  .question-row > :nth-child(4),
  .question-row > :nth-child(5) { display: none; }
}
</style>
