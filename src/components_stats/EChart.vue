<script setup lang="ts">
// ==========================================================================
//
// One ECharts instance, wrapped so no component has to remember the four
// things that are easy to get wrong:
//
//   1. dispose on unmount. ECharts attaches a resize listener and retains the
//      canvas; a route change without dispose leaks both, and the stats page
//      holds seven charts.
//   2. resize on container change, not on window resize. The stats grid
//      reflows when a section is collapsed, which never fires a window event.
//      A ResizeObserver catches both.
//   3. repaint on theme change. Colours come from CSS custom properties, so a
//      theme switch has to re-read them and re-set the option.
//   4. do not render into a zero-height box. ECharts silently draws nothing
//      and leaves no warning, which is indistinguishable from "no data".
// ==========================================================================
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import { echarts, readChartTheme, type ChartTheme } from '@/lib/charts/echarts';
import { currentTheme } from '@/lib/theme';

const props = defineProps<{
  /** Builds the ECharts option from the freshly-read theme. */
  option: (theme: ChartTheme) => Record<string, unknown>;
  /** When false the chart is not drawn and the slot content shows instead. */
  hasData?: boolean;
  /** Accessible description; also the empty-state text. */
  label?: string;
}>();

const host = ref<HTMLDivElement | null>(null);
const chart = shallowRef<echarts.ECharts | null>(null);
let observer: ResizeObserver | null = null;

/**
 * The option, built inside a computed so that every reactive value the builder
 * READS becomes a dependency of the repaint.
 *
 * this was `watch(() => [props.option, props.hasData, currentTheme.value])`
 * on the stated assumption that "a data change produces a new identity". It
 * does not. Every section declares its builder as an arrow function in setup(),
 * so `props.option` holds one reference for the component's whole lifetime and
 * a data change tracked nothing at all.
 *
 * The first paint still worked, which is exactly what hid it: `hasData` flips
 * false -> true when the rows land, and that IS tracked. Changing a filter
 * afterwards - data on both sides, so `hasData` never moves - left all seven
 * charts showing the previous selection with the new one in the tiles beside
 * them. Calling the builder inside a computed fixes it at the root: whatever
 * props or refs it touches are tracked automatically, with no list to maintain.
 */
const built = computed(() => {
  // Read both before any early return so both are tracked on every pass.
  const el = host.value;
  const enabled = props.hasData !== false;
  // Colours come from CSS custom properties, which are not reactive on their
  // own - touching the theme ref is what makes a theme switch repaint.
  void currentTheme.value;
  if (!el || !enabled) return null;
  return props.option(readChartTheme(el));
});

function draw() {
  const option = built.value;
  if (!host.value || option === null) return;
  if (!chart.value) chart.value = echarts.init(host.value, undefined, { renderer: 'canvas' });
  chart.value.setOption(option, true);
  // the instance is reachable from the DOM node in development so a chart
  // that renders nothing can be inspected without adding a probe each time.
  // A blank canvas and a broken option look identical from the outside.
  if (import.meta.env.DEV) (host.value as unknown as { __chart?: unknown }).__chart = chart.value;
}

onMounted(() => {
  draw();
  observer = new ResizeObserver(() => {
    // A collapsed section reports 0x0; resizing to that then back loses the
    // aspect ratio, so skip while hidden.
    if (host.value && host.value.clientHeight > 0) chart.value?.resize();
  });
  if (host.value) observer.observe(host.value);
});

// `flush: 'post'` so the canvas element exists before the first draw when
// `hasData` has just flipped and the template swapped the empty state out.
watch(built, () => draw(), { flush: 'post' });

onBeforeUnmount(() => {
  observer?.disconnect();
  chart.value?.dispose();
  chart.value = null;
});
</script>

<template>
  <div class="echart-host">
    <div v-if="hasData === false" class="echart-empty">
      <slot>
        <p>{{ label ? `No ${label} yet` : 'No data yet' }}</p>
        <p class="echart-empty-hint">Finish a paper and it will appear here.</p>
      </slot>
    </div>
    <div v-else ref="host" class="echart-canvas" role="img" :aria-label="label" />
  </div>
</template>

<style scoped lang="scss">
.echart-host { width: 100%; height: 100%; min-height: 0; position: relative; }
.echart-canvas { width: 100%; height: 100%; min-height: 0; }

.echart-empty {
  width: 100%; height: 100%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0.25rem; text-align: center; padding: 1rem;

  p { margin: 0; color: var(--muted); font-family: var(--font-body); font-size: 0.85rem; }
  .echart-empty-hint { font-size: 0.75rem; opacity: 0.7; }
}
</style>
