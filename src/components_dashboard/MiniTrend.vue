<!-- ========================================================================

Small, dependency-free SVG trend plot for the rotating dashboard summary. It
accepts nulls so a day with no marked paper is not drawn as zero accuracy.
============================================================================ -->
<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  values: Array<number | null>;
  label: string;
  color?: string;
}>(), {
  color: 'var(--series-1)',
});

const WIDTH = 320;
const HEIGHT = 150;
const PAD = 12;

const plotted = computed(() => {
  const numeric = props.values.filter((value): value is number => value !== null);
  if (!numeric.length) return [];
  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  const span = max - min;
  return props.values.map((value, index) => {
    if (value === null) return null;
    const x = props.values.length === 1
      ? WIDTH / 2
      : PAD + index * ((WIDTH - PAD * 2) / (props.values.length - 1));
    const y = span === 0
      ? HEIGHT / 2
      : PAD + (max - value) * ((HEIGHT - PAD * 2) / span);
    return { x, y, value };
  });
});

const path = computed(() => {
  let command = '';
  let drawing = false;
  for (const point of plotted.value) {
    if (!point) {
      drawing = false;
      continue;
    }
    command += `${drawing ? ' L' : ' M'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
    drawing = true;
  }
  return command.trim();
});

const numericValues = computed(() => (
  props.values.filter((value): value is number => value !== null)
));
const summary = computed(() => {
  if (!numericValues.value.length) return `${props.label}: no recent data`;
  const first = numericValues.value[0]!;
  const last = numericValues.value[numericValues.value.length - 1]!;
  return `${props.label}: ${first.toFixed(2)} to ${last.toFixed(2)} over fourteen days`;
});
</script>

<template>
  <div class="mini-trend" :style="{ '--spark-color': color }">
    <svg
      viewBox="0 0 320 150"
      role="img"
      :aria-label="summary"
      preserveAspectRatio="none"
    >
      <line v-for="y in [37.5, 75, 112.5]" :key="y" x1="0" :y1="y" x2="320" :y2="y" />
      <path v-if="path" :d="path" />
      <circle
        v-for="(point, index) in plotted"
        v-show="point"
        :key="index"
        :cx="point?.x"
        :cy="point?.y"
        r="2.5"
      />
    </svg>
    <span v-if="!path">No activity in this window</span>
    <small>14 days ago</small>
    <small>today</small>
  </div>
</template>

<style scoped>
.mini-trend {
  position: absolute;
  inset: 3.4rem 1rem 1rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: end;
  color: var(--muted);
}

svg {
  grid-column: 1 / -1;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: visible;
}

line {
  stroke: var(--chart-grid);
  stroke-width: 1;
}

path {
  fill: none;
  stroke: var(--spark-color);
  stroke-width: 4;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

circle {
  fill: var(--secondary-background);
  stroke: var(--spark-color);
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}

.mini-trend > span {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 0.75rem;
}

small {
  padding-top: 0.35rem;
  font-size: 0.64rem;
  opacity: 0.8;
}

small:last-child { text-align: right; }
</style>
