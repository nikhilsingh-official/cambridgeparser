<script setup lang="ts">;
import { defineProps, watch } from 'vue';
import Card from './Card.vue';

interface Card {
  color: string;
  subject: string;
  code: string;
  variant: string;
  condensed: string;
  icon: string;
}

const props = defineProps<{
  array: Card[];
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