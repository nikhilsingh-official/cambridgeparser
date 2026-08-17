<script setup lang="ts">
import { ref } from 'vue';
import { ChevronLeft, ChevronRight, LayoutGrid } from 'lucide-vue-next';
import SideWindowQuestion from './SideWindowQuestion.vue';
import { getShowStates } from './composable';

const { showOverview } = getShowStates();
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
        <div class="subheading-wrapper">
            <h3>No.</h3>
            <h3>Actions</h3>
        </div>
      </div>
      <SideWindowQuestion
        v-for="i in 40"
        :key="i"
        :question-num="i"
      />
    </div>
</template>

<style lang="scss" scoped>

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