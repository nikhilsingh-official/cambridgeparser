<script lang="ts" setup>
// the <Sidebar> element and its import were removed here - the app shell in
// App.vue renders one sidebar for every page now, so a page rendering its own
// produced two.
import Hero from './Hero.vue';
import StatsPrev from './StatsPrev.vue';
import QuickView from './QuickView.vue';
import MetaBar from '@/components/MetaBar.vue';
// the dashboard reads once here and hands the result to both panels, so
// they cannot show figures from two different fetches. See
// lib/dashboard/useDashboard.ts for why this is not useStats().
import { useDashboard } from '@/lib/dashboard/useDashboard';

// the dashboard preview consumes the same recent-series model as its totals.
const { loading, totals, streaks, recent, activitySeries } = useDashboard();
</script>
<template>
    <div class = "main-grid">
        <div class = "metabar-container">
          <MetaBar></MetaBar>
        </div>
        <Hero></Hero>
        <!-- pass real daily values into the formerly empty rotating panel. -->
        <StatsPrev
          :recent="recent"
          :series="activitySeries"
          :loading="loading"
        ></StatsPrev>
        <QuickView
          :papers="totals.papers"
          :marks-awarded="totals.marksAwarded"
          :marks-total="totals.marksTotal"
          :time-ms="totals.timeMs"
          :streak="streaks"
          :loading="loading"
        ></QuickView>
    </div>
</template>
<style lang="scss" scoped>
.main-grid {
  @extend %filler;
  color: $text;
  background-color: $background;
  display: grid;
  grid-template-columns: repeat(20, 1fr);
  /* minmax(0, 1fr) prevents child min-content sizes from stretching the
     twenty nominal rows beyond the viewport on the dashboard's first paint. */
  grid-template-rows: repeat(20, minmax(0, 1fr));
  position: relative;
  padding-left: 5vw;
}
.metabar-container {
  grid-row: 1/3;
  grid-column: 4 / 18;
}
</style>
