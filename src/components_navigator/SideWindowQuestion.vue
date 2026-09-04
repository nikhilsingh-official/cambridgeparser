<script setup lang="ts">
// this row was entirely placeholder - correctOption = ref(1),
// eliminatedOptions = ref([0,2,3]) and all three flags hardcoded to true, so
// every question in the Overview claimed the same invented answers. It now
// renders the real state for one question.
import { Flag, Star, Save } from 'lucide-vue-next';
import { computed } from 'vue';
import { OPTION_LETTERS } from '@/lib/types/enums';
import type { QuestionState } from '@/lib/state/examState';

const props = defineProps<{ question: QuestionState }>();
// the parent owns PDF navigation; this row only names the requested item.
const emit = defineEmits<{ (event: 'navigate', questionNumber: number): void }>();

// option count comes from the parsed paper rather than assuming four -
// paper_answers.option_count exists precisely because it is not always 4.
const letters = computed(() =>
  OPTION_LETTERS.slice(0, props.question.optionCount),
);
</script>

<template>
  <!-- a real button makes Overview navigation keyboard-accessible. -->
  <button
    type="button"
    class="side-window-question-wrapper"
    :class="{ answered: question.selected !== null }"
    :aria-label="`Go to question ${question.questionNumber}`"
    @click="emit('navigate', question.questionNumber)"
  >
    <span class="question-number">{{ question.questionNumber }}</span>
    <div class="indicators-wrapper">
      <!-- Overview mirrors the PDF state; it cannot mutate highlights.
           Render indicators as indicators instead of inert buttons. -->
      <span
        v-for="(letter, i) in letters"
        :key="letter"
        class="option-btn"
        :class="{
          correct: question.selected === i,
          eliminated: question.eliminated.includes(i),
        }"
        :aria-label="`Question ${question.questionNumber} option ${letter}`"
      >{{ letter }}</span>
    </div>
    <div class="indicators-wrapper">
      <div class="indicator-wrapper">
        <div class="icon flag-icon" :class="{ 'active': question.flagged }"><Flag /></div>
      </div>
      <div class="indicator-wrapper">
        <div class="icon star-icon" :class="{ 'active': question.difficult }"><Star /></div>
      </div>
      <div class="indicator-wrapper">
        <div class="icon save-icon" :class="{ 'active': question.saved }"><Save /></div>
      </div>
    </div>
  </button>
</template>
<style lang="scss" scoped>
.side-window-question-wrapper {
  display: grid;
  grid-template-columns: 26px 1fr auto;
  align-items: center;
  width: 100%;
  padding: 0.8vw 1vw;
  /* reset native button chrome while retaining keyboard semantics. */
  border-top: 0;
  border-right: 0;
  border-left: 0;
  border-bottom: $tertiary-background 1px solid;
  background: transparent;
  text-align: left;
  cursor: pointer;

  /* expose mouse and keyboard navigation state with the theme accent. */
  &:hover,
  &:focus-visible {
    background: color-mix(in srgb, $accent 8%, transparent);
  }

  &:focus-visible {
    outline: 2px solid $accent;
    outline-offset: -2px;
  }
}

.question-number {
  margin-right: auto; 
  font-family: 'Inter';
  color: $text;
}

.indicators-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 5px;
  height: 100%;
}

.option-btn {
    aspect-ratio: 1/1;
    border-radius: 5px;
    border: $accent 1px solid;
    height: 100%;
    background-color: transparent;
    color: $text;
    display: flex;
    align-items: center;
    justify-content: center;
}

.option-btn.correct {
    border: $success 1px solid;
    background-color: $success-darkened;
}

.option-btn.eliminated {
    border: $danger 1px solid;
    background-color: $danger-darkened;
}

.indicator-wrapper {
    height: 100%;
    .icon {
        svg {
            stroke: $text;
            opacity: 0.6;
        }
    }
}

.answered-icon.active svg {
  stroke: $accent;
  fill: $primary-color;
  opacity: 0.9 !important;
}

.flag-icon.active svg {
  stroke: $danger;
  fill: $danger-darkened;
  opacity: 1 !important;
}

.star-icon.active svg {
  stroke: $warning;
  fill: $warning-darkened;
  opacity: 1 !important;
}

.save-icon.active svg {
  stroke: $success;
  fill: $success-darkened;
  opacity: 0.9 !important;
}
</style>
