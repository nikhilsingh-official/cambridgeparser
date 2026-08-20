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
import { subjectNameFromSchema } from '@/constants/subjectCodes';

const props = defineProps<{
  summary: ExamSummary | null;
  /** Set while the attempt is still being written to Supabase. */
  saving?: boolean;
  /** Non-null when persistence failed; the score is still shown. */
  saveError?: string | null;
}>();

const emit = defineEmits<{
  (e: 'dashboard'): void;
  (e: 'review'): void;
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

// colour band for the ring. Deliberately NOT presented as a Cambridge
// grade - grade boundaries are per-paper and are not modelled anywhere yet.
const band = computed(() => {
  const p = props.summary?.percentage ?? 0;
  if (p >= 80) return 'strong';
  if (p >= 60) return 'fair';
  return 'weak';
});

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
      <div class="score-ring" :class="band" :style="ringStyle">
        <div class="score-inner">
          <p class="pct">{{ shownPercentage }}<span>%</span></p>
          <p class="marks">{{ summary.marksAwarded }} / {{ summary.marksTotal }} marks</p>
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

/* ---- score ring ---------------------------------------------------- */
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
