// ==========================================================================
//
// ECharts, registered piecemeal.
//
// Importing 'echarts' pulls the whole library (~1 MB). Every chart on the
// stats page is a line, bar, scatter, pie or heatmap, so only those renderers
// and the handful of components they need are registered here. Anything the
// page does not draw stays out of the bundle - the same discipline the
// manualChunks split in vite.config.ts already applies to pdf.js and lottie.
//
// If a new chart type is added, register it HERE rather than importing
// 'echarts' directly in a component: a single direct import anywhere undoes
// the tree-shaking for the whole app.
// ==========================================================================
import * as echarts from 'echarts/core';
import { LineChart, BarChart, ScatterChart, PieChart, HeatmapChart } from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DatasetComponent,
  MarkLineComponent,
  VisualMapComponent,
  TitleComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { LabelLayout, UniversalTransition } from 'echarts/features';

echarts.use([
  LineChart, BarChart, ScatterChart, PieChart, HeatmapChart,
  GridComponent, TooltipComponent, LegendComponent, DatasetComponent,
  MarkLineComponent, VisualMapComponent, TitleComponent,
  LabelLayout, UniversalTransition,
  CanvasRenderer,
]);

export { echarts };
export type { EChartsOption } from 'echarts';

/**
 * The chart palette, read from the active theme's CSS custom properties.
 *
 * Colours live in themes.scss (validated there as a set per surface) rather
 * than as hex constants in TypeScript, so a theme switch repaints the charts
 * without a rebuild and there is exactly one place a colour is defined. This
 * must be called AFTER mount - custom properties do not resolve on an element
 * that is not in the document.
 */
export interface ChartTheme {
  series: string[];
  sequential: string[];
  grid: string;
  axis: string;
  text: string;
  muted: string;
  surface: string;
  success: string;
  danger: string;
  fontBody: string;
  fontMono: string;
}

export function readChartTheme(el: HTMLElement = document.body): ChartTheme {
  const s = getComputedStyle(el);
  const v = (name: string, fallback: string) => s.getPropertyValue(name).trim() || fallback;
  return {
    // Fixed order, never cycled: slot N always belongs to the same entity, so
    // a filter that removes a subject does not repaint the survivors.
    series: [
      v('--series-1', '#3987e5'), v('--series-2', '#d95926'),
      v('--series-3', '#199e70'), v('--series-4', '#c98500'),
      v('--series-5', '#d55181'), v('--series-6', '#008300'),
    ],
    sequential: [
      v('--seq-0', '#1f242b'), v('--seq-1', '#1c4f45'), v('--seq-2', '#1a7a63'),
      v('--seq-3', '#21a37e'), v('--seq-4', '#4fd1a5'),
    ],
    grid: v('--chart-grid', 'rgba(255,255,255,0.06)'),
    axis: v('--chart-axis', '#8a93a0'),
    text: v('--text', '#fafafa'),
    muted: v('--muted', '#9a9a9a'),
    surface: v('--secondary-background', '#1a1a1a'),
    success: v('--success', '#4fd1a5'),
    danger: v('--danger', '#d95151'),
    fontBody: v('--font-body', 'Inter, sans-serif'),
    fontMono: v('--font-mono', 'monospace'),
  };
}

/**
 * Shared axis/grid styling. Grid lines and axes are deliberately recessive -
 * they are scaffolding, and every pixel of ink they take is ink the data is
 * not using.
 */
export function baseAxis(theme: ChartTheme) {
  return {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: theme.axis, fontFamily: theme.fontBody, fontSize: 11 },
    splitLine: { lineStyle: { color: theme.grid, width: 1 } },
  };
}

export function baseTooltip(theme: ChartTheme) {
  return {
    backgroundColor: theme.surface,
    borderColor: theme.grid,
    borderWidth: 1,
    padding: [8, 12] as [number, number],
    textStyle: { color: theme.text, fontFamily: theme.fontBody, fontSize: 12 },
    extraCssText: 'border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.25);',
  };
}
