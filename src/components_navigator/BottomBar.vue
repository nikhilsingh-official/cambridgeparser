<script setup lang="ts">
import { ref } from 'vue';
import { Wrench, LayoutGrid, FlagTriangleRight } from 'lucide-vue-next';
import { getShowStates } from './composable';

const { showOverview, showTools } = getShowStates()

// this bar had no way to finish a paper, which is why MCQNav.endExam() was
// unreachable and no attempt was ever written. A confirm step guards it -
// ending is irreversible and it sits next to two harmless toggles.
const confirming = ref(false);
const emit = defineEmits<{ (e: 'endExam'): void }>();

function onEndClick() {
  if (!confirming.value) {
    confirming.value = true;
    window.setTimeout(() => { confirming.value = false; }, 4000);
    return;
  }
  emit('endExam');
}
</script>
<template>
    <div class="bottom-bar">
      <div class="exam-code-container">
        <p>0625_w22_21</p>
      </div>
      <div class="drawers-caller">
        <div class="tools-wrapper" @click="showTools = !showTools">
          <Wrench></Wrench>
          <p>Tools</p>
        </div>
        <div class="overview-wrapper" @click="showOverview = !showOverview">
          <LayoutGrid></LayoutGrid>
          <p>Overview</p>
        </div>
      </div>
      <!-- End Exam control. Two-step: first click arms, second confirms. -->
      <div class="end-exam-wrapper" :class="{ armed: confirming }" @click="onEndClick">
        <FlagTriangleRight />
        <p>{{ confirming ? 'Confirm end?' : 'End Exam' }}</p>
      </div>
      <div class="save-container">
        <div class="dot-save-indicator"></div>
        <p>Saved</p>
      </div>
    </div>
</template>
<style lang="scss" scoped>
/* styled to sit alongside the existing .tools-wrapper / .overview-wrapper,
   but tinted with $danger once armed so the second click is clearly different. */
.end-exam-wrapper {
  display: flex;
  align-items: center;
  column-gap: 6px;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 50px;
  border: 1px solid transparent;
  transition: background 0.3s ease, border-color 0.3s ease, color 0.3s ease;

  svg { width: 18px; height: 18px; }
  p { margin: 0; font-family: 'Lexend'; font-size: 12px; }

  &:hover { border-color: rgba(255, 255, 255, 0.18); }
  &.armed {
    border-color: $danger;
    color: $danger;
    svg { stroke: $danger; }
  }
}

.bottom-bar {
  flex: 0 0 auto;
  min-height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.3rem;
  gap: 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  .exam-code-container {
    color: lightgray;
    font-family: 'Kode Mono';
    font-size: 13.5px;
  }
  .drawers-caller {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    .tools-wrapper, .overview-wrapper {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 7.5px;
      svg {
        stroke: $accent;
        width: 15px;
      }  
      color: $text;
      font-family: 'Inter';
      font-size: 13.5px;
      cursor: pointer;
    }
  }
  .save-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7.5px;
    .dot-save-indicator {
      width: 10px;
      aspect-ratio: 1/1;
      border-radius: 50%;
      background-color: $success;
    }
    color: $text;
    font-family: 'Inter';
    font-size: 13.5px;
  }
}
</style>