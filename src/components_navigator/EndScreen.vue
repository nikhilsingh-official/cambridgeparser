<script setup lang="ts">
// ==========================================================================
//
// End-of-exam results screen. Overlays the paper, mirroring LoadingScreen's
// role at the other end of the attempt, and reuses its visual language: the
// same gridded $secondary-background, Lexend/Inter/Kode Mono split, and pill
// buttons with the $secondary-color border and $accent glow on hover.
//
// The score is computed locally by buildExamSummary() from data the client
// already holds, so the screen paints instantly and still works if the attempt
// failed to persist. The database stays the authority on correctness.
// ==========================================================================
import { computed, ref, onMounted } from 'vue';
import { ChevronRight, RotateCcw, Check, X, Minus, Zap } from 'lucide-vue-next';
import { formatDuration, QuestionOutcome, type ExamSummary } from '@/lib/types/examSummary';
import {
  subjectNameFromSchema, subjectCodeFromSchema, paperNumberFromSchema,
} from '@/constants/subjectCodes';
import { readiness, gradeTone, isPaperCeiling, isTierCapped, MODEL } from '@/lib/stats/model';

const props = defineProps<{
  summary: ExamSummary | null;
  /** Set while the attempt is still being written to Supabase. */
  saving?: boolean;
  /** Non-null when persistence failed; the score is still shown. */
  saveError?: string | null;
  /** Only transactional failures are retryable; practice-only sessions are not. */
  canRetry?: boolean;
}>();

const emit = defineEmits<{
  (e: 'dashboard'): void;
  (e: 'review'): void;
  (e: 'retry'): void;
}>();

const subject = computed(() =>
  props.summary ? subjectNameFromSchema(props.summary.paperId) : '',
);

// the headline number counts up on mount. Cosmetic, but it gives the
// screen a beat of its own rather than snapping in at full value.
const shownPercentage = ref(0);
onMounted(() => {
  const target = props.summary?.percentage ?? 0;
  if (target <= 0) return;
  const durationMs = 900;
  const start = performance.now();
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / durationMs);
    // ease-out cubic
    shownPercentage.value = Math.round(target * (1 - Math.pow(1 - t, 3)) * 10) / 10;
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
});

/**
 * the grade this score would have earned on this component.
 *
 * The comment that used to sit here said grade boundaries "are not modelled
 * anywhere yet" and the ring was banded on invented 80/60 cut-offs. Both are
 * now wrong: src/constants/gradeThresholds.ts holds Cambridge's own published
 * thresholds for this exact paper - the session and variant are in the schema -
 * and model.ts turns them into a grade with an interval around it.
 *
 * On a multiple-choice component grade A averages 66%, so the old rule painted
 * a real A as merely "fair" - the kind of error that quietly tells a student
 * they are doing worse than they are.
 */
const grade = computed(() => {
  const s = props.summary;
  if (!s) return null;
  return readiness(
    s.marksAwarded,
    s.marksTotal,
    s.results.length,
    subjectCodeFromSchema(s.paperId),
    paperNumberFromSchema(s.paperId),
    // the schema itself, so the grade comes from THIS paper's published
    // boundary rather than the component mean. It is one specific past paper -
    // we know which session set the boundary, so averaging it away would be
    // discarding the answer.
    s.paperId,
  );
});

// The ring now takes its colour from the grade rather than from a percentage,
// so what it signals matches what the letter beside it says.
const band = computed(() =>
  grade.value?.reliable ? gradeTone(grade.value.grade) : 'fair');

// a Core-tier paper caps at C. Scoring 83% on one and being shown a C
// reads as a bug unless the screen says why, so it does - and points at the
// paper where the same marks would be worth more.
//
// Both halves are required. Hitting an A on the Extended paper is also "the
// ceiling", and telling someone who has just got an A that they have run into
// a limit would be absurd, so the tier test gates the message.
const atCeiling = computed(() =>
  !!grade.value?.reliable
  && isTierCapped(grade.value.thresholds)
  && isPaperCeiling(grade.value.grade, grade.value.thresholds));

const ringStyle = computed(() => ({
  // conic-gradient sweep for the score ring
  '--sweep': `${Math.min(100, props.summary?.percentage ?? 0)}%`,
}));

function outcomeIcon(outcome: QuestionOutcome) {
  if (outcome === QuestionOutcome.Correct) return Check;
  if (outcome === QuestionOutcome.Incorrect) return X;
  return Minus;
}
</script>

<template>
  <div class="end-screen">
    <div v-if="summary" class="centered-content">

      <header class="result-header">
        <h5 class="paper-code">{{ subject }} · {{ summary.paperId }}</h5>
        <h3>Paper complete</h3>
      </header>

      <!-- score ring - the one thing the candidate actually wants -->
      <div class="score-row">
        <div class="score-ring" :class="band" :style="ringStyle">
          <div class="score-inner">
            <p class="pct">{{ shownPercentage }}<span>%</span></p>
            <p class="marks">{{ summary.marksAwarded }} / {{ summary.marksTotal }} marks</p>
          </div>
        </div>

        <!-- the grade, with everything needed to read it honestly - which
             component it is for, how wide the estimate is, and that the
             boundary itself moves between sessions. A bare letter would be a
             more confident claim than the data supports. -->
        <div v-if="grade?.reliable" class="grade-card" :class="band">
          <p class="grade-label">would have been</p>
          <p class="grade-letter">{{ grade.grade }}</p>
          <p class="grade-range">
            {{ grade.best === grade.worst ? 'firm at this mark' : `${grade.best}–${grade.worst} range` }}
          </p>
          <p v-if="atCeiling" class="grade-ceiling">
            {{ grade.grade }} is the highest this paper awards — the higher grades
            are only on the Extended paper.
          </p>
          <!-- which boundary this was read against. The two claims are
               not the same strength - one is what the examiner published for
               this paper, the other is what an average paper would have
               needed - so the note says which, rather than one line covering
               both. -->
          <p class="grade-note">
            <template v-if="grade.basis === 'session'">
              this paper only, against its own {{ grade.thresholds!.session }} boundaries
            </template>
            <template v-else>
              this paper only; no boundaries published for this session, so
              {{ grade.thresholds!.years[0] }}–{{ grade.thresholds!.years[1] }} averaged over
              {{ grade.thresholds!.grades[grade.grade as 'A']?.n ?? 0 }} sessions
            </template>
          </p>
        </div>
        <div v-else class="grade-card unknown">
          <p class="grade-label">grade estimate</p>
          <p class="grade-letter">&mdash;</p>
          <p class="grade-range">
            {{ grade && !grade.thresholds ? 'no published boundaries' : 'too few questions' }}
          </p>
          <p class="grade-note">
            {{ grade && !grade.thresholds
              ? 'Cambridge boundaries for this component were not found.'
              : `A grade needs at least ${MODEL.grade.minQuestions} questions behind it.` }}
          </p>
        </div>
      </div>

      <!-- outcome counts -->
      <div class="tile-row">
        <div class="tile correct">
          <p class="tile-value">{{ summary.correctCount }}</p>
          <p class="tile-label">Correct</p>
        </div>
        <div class="tile incorrect">
          <p class="tile-value">{{ summary.incorrectCount }}</p>
          <p class="tile-label">Incorrect</p>
        </div>
        <div class="tile unanswered">
          <p class="tile-value">{{ summary.unansweredCount }}</p>
          <p class="tile-label">Unanswered</p>
        </div>
        <div class="tile">
          <p class="tile-value">{{ formatDuration(summary.durationMs) }}</p>
          <p class="tile-label">Total time</p>
        </div>
        <div class="tile">
          <p class="tile-value">{{ Math.round(summary.averageTimePerQuestion) }}s</p>
          <p class="tile-label">Avg / question</p>
        </div>
      </div>

      <!-- surfaced separately because correct guesses inflate the score
           above and hide exactly the gaps worth revising. -->
      <p v-if="summary.luckyGuessCount > 0" class="guess-note">
        <Zap class="icon" />
        {{ summary.luckyGuessCount }} correct
        {{ summary.luckyGuessCount === 1 ? 'answer looks' : 'answers look' }}
        like a guess &mdash; worth revisiting.
      </p>

      <!-- per-question strip. Hover shows what was picked vs the key. -->
      <div class="breakdown">
        <div
          v-for="r in summary.results"
          :key="r.questionNumber"
          class="q-cell"
          :class="r.outcome"
          :title="`Q${r.questionNumber} — you: ${r.selected ?? '—'} · answer: ${r.correct ?? '?'}`"
        >
          <component :is="outcomeIcon(r.outcome)" class="q-icon" />
          <span class="q-num">{{ r.questionNumber }}</span>
        </div>
      </div>

      <div class="save-state">
        <span v-if="saving" class="saving">Saving attempt…</span>
        <span v-else-if="saveError" class="save-failed" :title="saveError">
          Results shown locally — attempt not saved
          <button v-if="canRetry" type="button" @click="emit('retry')">Retry save</button>
        </span>
        <span v-else class="saved">Attempt saved</span>
      </div>

      <div class="button-container">
        <button class="ghost" @click="emit('review')">
          <RotateCcw class="icon" /> Review paper
        </button>
        <button class="primary" @click="emit('dashboard')">
          Go to dashboard <ChevronRight class="icon" />
        </button>
      </div>
    </div>

    <!-- endExam() is async; this covers the gap before the summary exists. -->
    <div v-else class="centered-content">
      <h3>Marking your paper…</h3>
    </div>
  </div>
</template>

<style lang="scss" scoped>
// same gridded backdrop as LoadingScreen so the two bookends match.
.end-screen {
  background-color: $secondary-background;
  background-image:
    linear-gradient(to right, $background 1px, transparent 1px),
    linear-gradient(to bottom, $background 1px, transparent 1px);
  background-size: 30px 30px;
  width: 100%;
  height: 100%;
  position: absolute;
  left: 0;
  top: 0;
  z-index: 1000;
  color: $text;
  overflow-y: auto;
}

.centered-content {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 40px 24px;
}

.result-header {
  text-align: center;
  h3 { font-family: 'Lexend'; margin: 4px 0 0; }
  .paper-code {
    font-family: 'Kode Mono';
    opacity: 0.5;
    margin: 0;
  }
}

/* ---- score ring + grade -------------------------------------------- */
/* the ring and the grade sit side by side rather than stacked - they are
   the same fact stated two ways, and separating them vertically would invite
   reading the grade as a second, independent result. */
.score-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 28px;
  flex-wrap: wrap;
}

.grade-card {
  --tone: #{$secondary-color};
  text-align: left;
  padding: 16px 20px;
  border-radius: 16px;
  background: $tertiary-background;
  /* A left rule rather than a tinted fill: the ring beside it already carries
     the colour, and two saturated blocks would compete. */
  border-left: 3px solid var(--tone);
  max-width: 260px;

  &.strong { --tone: #{$success}; }
  &.fair   { --tone: #{$warning}; }
  &.weak   { --tone: #{$danger}; }
  &.unknown { --tone: #{$muted}; }

  .grade-label {
    font-family: 'Lexend';
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.5;
    margin: 0;
  }
  .grade-letter {
    font-family: 'Kode Mono';
    font-size: 52px;
    line-height: 1;
    margin: 2px 0 0;
    color: var(--tone);
  }
  .grade-range {
    font-family: 'Lexend';
    font-size: 12px;
    opacity: 0.65;
    margin: 6px 0 0;
  }
  .grade-note {
    font-family: 'Lexend';
    font-size: 10.5px;
    line-height: 1.4;
    opacity: 0.4;
    margin: 6px 0 0;
  }
  /* Brighter than the provenance note below it: this one changes what the
     student should do next, rather than explaining where a number came from. */
  .grade-ceiling {
    font-family: 'Lexend';
    font-size: 11px;
    line-height: 1.4;
    color: var(--tone);
    opacity: 0.85;
    margin: 8px 0 0;
  }
  /* An unavailable grade is dimmed AND an em dash - never a letter that
     happens to look small. */
  &.unknown .grade-letter { opacity: 0.3; }
}

.score-ring {
  --ring: #{$secondary-color};
  width: 200px;
  height: 200px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(var(--ring) var(--sweep), $tertiary-background 0);
  transition: background 0.6s ease;

  &.strong { --ring: #{$success}; }
  &.fair   { --ring: #{$warning}; }
  &.weak   { --ring: #{$danger}; }

  .score-inner {
    width: 168px;
    height: 168px;
    border-radius: 50%;
    background: $secondary-background;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  .pct {
    font-family: 'Lexend';
    font-size: 44px;
    margin: 0;
    line-height: 1;
    span { font-size: 20px; opacity: 0.6; }
  }
  .marks {
    font-family: 'Kode Mono';
    font-size: 12px;
    opacity: 0.6;
    margin: 6px 0 0;
  }
}

/* ---- stat tiles ------------------------------------------------------ */
.tile-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}
.tile {
  background: $tertiary-background;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 12px 18px;
  min-width: 96px;
  text-align: center;

  .tile-value {
    font-family: 'Lexend';
    font-size: 20px;
    margin: 0;
  }
  .tile-label {
    font-family: 'Inter';
    font-size: 11px;
    opacity: 0.55;
    margin: 2px 0 0;
  }
  &.correct   .tile-value { color: $success; }
  &.incorrect .tile-value { color: $danger; }
  &.unanswered .tile-value { opacity: 0.6; }
}

.guess-note {
  font-family: 'Inter';
  font-size: 12px;
  opacity: 0.75;
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  .icon { width: 14px; height: 14px; stroke: $warning; }
}

/* ---- per-question breakdown ----------------------------------------- */
.breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
  max-width: 620px;
}
.q-cell {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: $tertiary-background;
  border: 1px solid transparent;
  cursor: default;
  transition: transform 0.15s ease;

  &:hover { transform: translateY(-2px); }

  .q-icon { width: 12px; height: 12px; }
  .q-num {
    font-family: 'Kode Mono';
    font-size: 9px;
    opacity: 0.6;
  }
  &.correct    { border-color: $success; .q-icon { stroke: $success; } }
  &.incorrect  { border-color: $danger;  .q-icon { stroke: $danger; } }
  &.unanswered { opacity: 0.45; }
}

/* ---- save state ------------------------------------------------------ */
.save-state {
  font-family: 'Kode Mono';
  font-size: 11px;
  opacity: 0.55;
  .save-failed { color: $warning; }
}

/* ---- actions (LoadingScreen's pill button, same hover) --------------- */
.button-container {
  display: flex;
  gap: 12px;
  padding: 4px;
  flex-wrap: wrap;
  justify-content: center;

  button {
    cursor: pointer;
    font-family: 'Lexend';
    display: flex;
    align-items: center;
    justify-content: center;
    column-gap: 6px;
    border: $secondary-color 2px solid;
    padding: 0.67vw 1.4vw;
    border-radius: 50px;
    font-size: 13px;
    transition: background 1s ease, box-shadow 0.5s ease;
    color: $text;
    background-color: transparent;

    &:hover {
      background-color: $secondary-color;
      box-shadow: 0px 0px 5px 1px $accent;
    }
    .icon { width: 18px; height: 18px; stroke-width: 2.4; }
  }
  .ghost {
    border-color: rgba(255, 255, 255, 0.18);
    &:hover {
      background-color: $tertiary-background;
      box-shadow: none;
    }
  }
}
</style>
