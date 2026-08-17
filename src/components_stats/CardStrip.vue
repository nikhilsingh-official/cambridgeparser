<script setup lang="ts">
import StatsCard from './StatsCard.vue';

const testStats = Array.from({ length: 30 }, (_, i) => {
  const category = i % 17
  const subjectCodes = ['0620', '0610', '0580', '0455', '0478', '0500']
  const text = category === 0 ? subjectCodes[i % subjectCodes.length] : `${Math.floor(Math.random() * 5000)}`
  const metricData = `${Math.floor(Math.random() * 50) + 50}%`
  return { category, text, metricData }
})
</script>
<template>
  <div class="card-strip">
    <StatsCard
      v-for="(card, index) in testStats"
      :key="index"
      :category="card.category"
      :text="card.text"
      :metric-data="card.metricData"
    />
  </div>
</template>
<style lang="scss" scoped>
.card-strip {
    width: 500%;
    height: 100%;
    display: flex;
    column-gap: 10px;
    background-color: $background;
    animation: infinite-side-scroll 100s linear infinite;
}
@keyframes infinite-side-scroll {
    0% {
        transform: translateX(0%);
    }
    100% {
        transform: translateX(-50%);
    }
}
</style>