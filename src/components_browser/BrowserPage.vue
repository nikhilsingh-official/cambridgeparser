<script setup lang="ts">
// this file used to be a 32-element hardcoded array of subject cards with
// invented paper codes, and a `selectedSubjects` prop the router never passed
// (so it was permanently `undefined`). The grid is now generated from
// constants/paperCatalogue.ts and joined to the user's real attempts - see
// lib/browser/usePaperBrowser.ts.
import CardGrid from './CardGrid.vue';
import Header from './Header.vue';
import { usePaperBrowser } from '@/lib/browser/usePaperBrowser';

const { filter, cards, visibleCards, loading, error } = usePaperBrowser();
</script>

<template>
  <div class="main-container">
    <div class="meta-container">
      <Header
        v-model="filter"
        :result-count="visibleCards.length"
        :total-count="cards.length"
      ></Header>
    </div>
    <div class = "grid-wrapper">
      <!-- the attempt overlay is the only thing that can fail; the
           catalogue is local. So a failure degrades to a grid with no badges
           rather than to a blank page. -->
      <p v-if="error" class="grid-notice">
        Could not load your attempt history ({{ error }}). Papers are still listed below.
      </p>
      <p v-else-if="loading" class="grid-notice">Loading your attempts...</p>
      <p v-else-if="!visibleCards.length" class="grid-notice">
        No papers match these filters. Widen the year, season or progress filter.
      </p>
      <CardGrid :array="visibleCards"></CardGrid>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.main-container {
  position: relative;
  width: 100%;
  z-index: 4;
  display: grid;
  grid-template-columns: repeat(20, 1fr);
  overflow-x: hidden;
  background-color: $background;
  padding-left: 5vw;
}
.meta-container {
  height: 70vh;
  grid-column: 3/19;
  display: flex;
}
.grid-wrapper {
  grid-column: 3/19;
  /* the grid used to be the last thing on the page with nothing below it.
     With a real catalogue it can run to hundreds of cards, so it needs room to
     breathe at the bottom rather than ending flush against the viewport. */
  padding-bottom: 4rem;
}
/* added - loading, empty and degraded states. There were none. */
.grid-notice {
  font-family: 'Lexend';
  font-weight: 300;
  color: $text;
  opacity: 0.7;
  padding-bottom: 1.5rem;
}
.flex-select-btn {
  display: flex;
  column-gap: 10px;
} 
</style>
