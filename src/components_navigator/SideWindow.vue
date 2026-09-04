<script setup lang="ts">
import { ChevronLeft, ChevronRight, LayoutGrid } from 'lucide-vue-next';
import SideWindowQuestion from './SideWindowQuestion.vue';
import { getShowStates } from './composable';
// the real per-question state, replacing the hardcoded 40 rows.
import { answeredCount, questionList } from '@/lib/state/examState';

const { showOverview } = getShowStates();
// pass the selected question to MCQNav, which owns the iframe and focus tree.
const emit = defineEmits<{ (event: 'navigate-question', questionNumber: number): void }>();
</script>

<template>
    <button
      class="overview-drawer__toggle"
      type="button"
      @click="showOverview = !showOverview"
    >
      <ChevronRight v-if="showOverview" />
      <ChevronLeft v-else />
    </button>

    <div class="side-window-questions">
      <div class="header-container">
        <div class="header-wrapper">
            <LayoutGrid></LayoutGrid>
            <h1> Overview</h1>
        </div>
        <!-- a live progress read-out; the panel previously showed no
             indication of how much of the paper was done. -->
        <p v-if="questionList.length" class="overview-progress">
          {{ answeredCount }} / {{ questionList.length }} answered
        </p>
        <div class="subheading-wrapper">
            <h3>No.</h3>
            <h3>Actions</h3>
        </div>
      </div>
      <!-- was `v-for="i in 40"` - a fixed 40 rows regardless of the paper,
           each rendering invented answers. Now driven by the parsed paper. -->
      <!-- each row bubbles its requested PDF question to MCQNav. -->
      <SideWindowQuestion
        v-for="q in questionList"
        :key="q.questionNumber"
        :question="q"
        @navigate="emit('navigate-question', $event)"
      />

      <!-- the panel used to look identical before and after the paper had
           been parsed. An explicit empty state says which it is. -->
      <p v-if="questionList.length === 0" class="overview-empty">
        Waiting for the paper to finish loading&hellip;
      </p>
    </div>
</template>

<style lang="scss" scoped>
/* overview progress read-out + empty state */
.overview-progress {
  font-family: $font-mono;
  font-size: 11px;
  color: $accent;
  opacity: 0.8;
  margin: 4px 0 0;
}
.overview-empty {
  font-family: $font-body;
  font-size: 12px;
  color: $muted;
  padding: 1rem;
  text-align: center;
}


.overview-drawer__toggle {
  position: absolute;
  left: -30px;
  top: 50%;
  transform: translateY(-50%);

  width: 30px;
  aspect-ratio: 5/8;
  border: none;
  outline: none;
  cursor: pointer;

  border-radius: 10px 0 0 10px;
  background-color: $secondary-background;
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    margin-left: 2px;
    width: 18px;
    height: 18px;
    stroke: $accent;
  }
}

.side-window-questions {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  background-color: $secondary-background;
  .header-container {
    padding: 0.8vw;
    display: flex;
    flex-direction: column;
    gap: 10px;
    .header-wrapper {
        display: flex;
        align-items: center;
        gap: 10px;
        h1 {
            font-size: 25px;
            font-family: 'Inter';
            color: $text;
        }
        svg {
            stroke: $accent;
        }
    }
    .subheading-wrapper {
        display: flex;
        align-items: center;
        justify-content: space-between;
        h3 {
            font-size: 15px;
            font-weight: 400;
            font-family: 'Inter';
            color: $text;
        }
    }
  }
}
</style>
