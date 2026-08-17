<script lang="ts" setup>
import Sidebar from '../components/Sidebar.vue';
import Hero from './Hero.vue';
import StatsPrev from './StatsPrev.vue';
import QuickView from './QuickView.vue';
import MetaBar from '@/components/MetaBar.vue';
</script>
<template>
    <Sidebar></Sidebar>
    <div class = "main-grid">
        <div class = "metabar-container">
          <MetaBar></MetaBar>
        </div>
        <Hero></Hero>
        <StatsPrev></StatsPrev>
        <QuickView></QuickView>
    </div>
</template>
<style lang="scss" scoped>
.main-grid {
  @extend %filler;
  color: $text;
  background-color: $background;
  display: grid;
  grid-template-columns: repeat(20, 1fr);
  grid-template-rows: repeat(20, 1fr);
  position: relative;
  padding-left: 5vw;
}
.metabar-container {
  grid-row: 1/3;
  grid-column: 4 / 18;
}
</style>