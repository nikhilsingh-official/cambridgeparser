<script setup lang="ts">
import Card from './Card.vue';
// was `Card as CardData` from constants/codeMaps - the mock's shape. The
// grid now carries real papers, so it carries PaperCard.
import type { PaperCard } from '@/lib/browser/usePaperBrowser';

// the `watch` that console.log'd 'Array changed:' on every render is gone.
const props = defineProps<{
  array: PaperCard[];
}>();
</script>

<template>
    <div class = "track">
        <!-- keyed by paper id, not by index. With a filter that reorders
             the list, an index key makes Vue reuse a card's DOM for a
             different paper - the artwork and the badge would be the previous
             paper's until something forced a repaint. -->
        <Card v-for="item in props.array"
            :key="item.id"
            :card="item">
        </Card>
    </div>
</template>

<style scoped>
.track {
  display: grid;
  width: 100%;
  height: 100%;
  grid-template-columns: repeat(auto-fit, minmax(350px, 350px));
  /* was `grid-template-rows: repeat(10, 1fr)`, which declared exactly ten
     rows. The mock had 32 cards in a 3-4 column layout, so it fit; a real
     filter can produce hundreds, and everything past row ten landed in an
     implicit row of height 0 - cards were being rendered on top of each other.
     Auto rows size to the cards instead. */
  grid-auto-rows: min-content;
  row-gap: 5px;
  column-gap: 5px;
  align-items: center;
  justify-content: center;
}
</style>
