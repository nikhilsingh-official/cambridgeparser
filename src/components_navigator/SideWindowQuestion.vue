<script setup lang="ts">
import { Flag, Star, Save, Circle } from 'lucide-vue-next';
import { ref } from 'vue';

const props = defineProps<{
  questionNum: number;
}>();

type OptionLetter = "A" | "B" | "C" | "D";
const OPTIONS_LETTER_MAP: OptionLetter[] = ["A", "B", "C", "D"];
const correctOption = ref(1);
const eliminatedOptions = ref([0, 2, 3]);
const isFlagged = ref(true);
const isDifficult = ref(true);
const isSaved = ref(true);

</script>

<template>
  <div class="side-window-question-wrapper">
    <span class="question-number">{{ props.questionNum }}</span>
    <div class="indicators-wrapper">
      <button class="option-btn" v-for="i in 4" :class="{ correct: correctOption == i - 1, eliminated: eliminatedOptions.includes(i - 1) }">{{ OPTIONS_LETTER_MAP[i - 1] }}</button>
    </div>
    <div class="indicators-wrapper">
      <div class="indicator-wrapper">
        <div class="icon flag-icon" :class="{ 'active': isFlagged }"><Flag /></div>
      </div>
      <div class="indicator-wrapper">
        <div class="icon star-icon" :class="{ 'active': isDifficult }"><Star /></div>
      </div>
      <div class="indicator-wrapper">
        <div class="icon save-icon" :class="{ 'active': isSaved }"><Save /></div>
      </div>
    </div>
  </div>
</template>
<style lang="scss" scoped>
.side-window-question-wrapper {
  display: grid;
  grid-template-columns: 26px 1fr auto;
  align-items: center;
  width: 100%;
  padding: 0.8vw 1vw;
  border-bottom: $tertiary-background 1px solid;
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
    cursor: pointer;
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
    cursor: pointer;
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