<script setup lang="ts">;
import { defineProps, watch } from 'vue';
import Card from './Card.vue';
// this file declared its own `interface Card` which BOTH shadowed the
// imported component of the same name AND differed from the Card interface in
// constants/codeMaps.ts (it required `color`, the other had no such field).
// TypeScript therefore saw two unrelated types called Card and rejected the
// assignment in BrowserPage. Now there is one shared shape.
import type { Card as CardData } from '@/constants/codeMaps';

const props = defineProps<{
  array: CardData[];
}>();

watch(() => props.array, (newArray) => {
  console.log('Array changed:', newArray);

}, { immediate: true });

</script>

<template>
    <div class = "track">
        <Card v-for="(item, index) in props.array" 
            :key="index"     
            :color="item.color" 
            :subject="item.subject"
            :code="item.code"
            :condensed="item.condensed"
            :variant="item.variant"
            :icon="item.icon" >
        </Card>
    </div>
</template>

<style scoped>
.track {
  display: grid;
  width: 100%;
  height: 100%;
  grid-template-columns: repeat(auto-fit, minmax(350px, 350px));
  grid-template-rows: repeat(10, 1fr);
  row-gap: 5px;
  column-gap: 5px;
  align-items: center;
  justify-content: center;
}
</style>