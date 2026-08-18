<script setup lang="ts">
// ==========================================================================
//
// Focus section, redesigned. The original is preserved at tag
// `stats-page-original` and had two structural problems:
//   - every slot sat in columns 1-7 of a 20-column grid, leaving ~70% of the
//     section empty;
//   - four tiles all carried the class `quickview-container-1`, so they
//     stacked invisibly in one cell.
//
// This section drops the fixed 20x20 grid (Progress and Engagement keep
// theirs) because its content is two large charts plus a metric bar, and
// forcing that into 20 equal rows only makes the panel sizes arbitrary.
//
// Chart canvases are left as empty, correctly-sized containers on purpose:
// the app performs zero reads until the query layer lands, and a chart drawn
// over placeholder data is worse than an honest empty state.
// See STATS_PAGE_DESIGN.md §3.1.
// ==========================================================================
import { Target, ScatterChart, Shuffle } from 'lucide-vue-next';

// the six tiles under the charts. All six come from v_question_flags.
// `value` stays null until the query layer exists - the template renders a
// muted em dash rather than a fake number.
interface FocusTile {
  label: string;
  value: string | null;
  /** Short reading of what the number means, shown under the value. */
  hint: string;
}

const tiles: FocusTile[] = [
  { label: 'Overconfident',   value: null, hint: 'sure, but wrong' },
  { label: 'Underconfident',  value: null, hint: 'right, but hesitant' },
  { label: 'Guesses',         value: null, hint: 'fast, no eliminations' },
  { label: 'Guess accuracy',  value: null, hint: 'how often luck held' },
  { label: 'Elim. precision', value: null, hint: 'ruled out correctly' },
  { label: 'Mean hesitation', value: null, hint: 'before first action' },
];
</script>

<template>
  <div class="focus-layout">

    <!-- row 1 - the two charts that carry the section -->
    <div class="chart-row">
      <div class="panel calibration-panel">
        <div class="panel-header">
          <Target class="panel-icon" />
          <div>
            <h4>Calibration</h4>
            <!-- labelled "behavioural" deliberately - this is inferred from
                 timing and eliminations, not a confidence the student stated.
                 See STATS_PAGE_DESIGN.md §0.2. -->
            <p class="panel-sub">behavioural confidence vs actual accuracy</p>
          </div>
        </div>
        <div class="chart-canvas" data-chart="calibration"></div>
        <p class="panel-legend">
          <span class="above"></span> above the line: you know more than you think
          <span class="below"></span> below: overconfident
        </p>
      </div>

      <div class="panel scatter-panel">
        <div class="panel-header">
          <ScatterChart class="panel-icon" />
          <div>
            <h4>Time vs correctness</h4>
            <p class="panel-sub">where your wrong answers come from</p>
          </div>
        </div>
        <div class="chart-canvas" data-chart="time-correctness"></div>
        <p class="panel-legend">
          fast &amp; unsure = guessing &nbsp;·&nbsp; slow &amp; sure = misconception
        </p>
      </div>
    </div>

    <!-- row 2 - full width. Empty until attempt_events is read; see §5. -->
    <div class="panel sankey-panel">
      <div class="panel-header">
        <Shuffle class="panel-icon" />
        <div>
          <h4>Answer changes</h4>
          <p class="panel-sub">first choice to final choice &mdash; is your instinct right?</p>
        </div>
      </div>
      <div class="chart-canvas chart-canvas-wide" data-chart="answer-sankey"></div>
    </div>

    <!-- row 3 - metric bar -->
    <div class="tile-row">
      <div v-for="tile in tiles" :key="tile.label" class="tile">
        <p class="tile-label">{{ tile.label }}</p>
        <p class="tile-value" :class="{ empty: tile.value === null }">
          {{ tile.value ?? '—' }}
        </p>
        <p class="tile-hint">{{ tile.hint }}</p>
      </div>
    </div>

  </div>
</template>

<style lang="scss" scoped>
// a column flow rather than the 20x20 grid the other two sections use.
// grid-column/grid-row span the whole section body so this sits inside the
// parent grid without being governed by it.
.focus-layout {
  grid-column: 1 / 21;
  grid-row: 1 / 21;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

// same card treatment as the other sections - $secondary-background,
// 20px radius - so the redesign does not read as a different page.
.panel {
  background-color: $secondary-background;
  border-radius: 20px;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  column-gap: 12px;
  margin-bottom: 0.75rem;

  h4 {
    font-family: 'Inter';
    font-weight: 400;
    color: $text;
    margin: 0;
    font-size: 1.05rem;
  }
  .panel-sub {
    font-family: 'Lexend';
    font-size: 0.75rem;
    color: $text;
    opacity: 0.45;
    margin: 2px 0 0;
  }
  .panel-icon {
    width: 22px;
    height: 22px;
    color: $accent;
    flex-shrink: 0;
    margin-top: 2px;
  }
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  flex: 1 1 0;
  min-height: 0;
}

// the ECharts mount point. It must have a real height before init() - a
// flex/percentage height that resolves to 0 is the single most common reason
// an ECharts canvas renders blank.
.chart-canvas {
  flex: 1 1 auto;
  min-height: 220px;
  border-radius: 12px;
  // faint hatch marks the panel as awaiting data rather than broken.
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
  background-size: 24px 24px;
}
.chart-canvas-wide { min-height: 200px; }

.panel-legend {
  font-family: 'Lexend';
  font-size: 0.7rem;
  color: $text;
  opacity: 0.4;
  margin: 0.6rem 0 0;
  display: flex;
  align-items: center;
  column-gap: 6px;
  flex-wrap: wrap;

  .above, .below {
    width: 8px;
    height: 8px;
    border-radius: 2px;
    display: inline-block;
  }
  .above { background-color: $success; }
  .below { background-color: $danger; }
}

.sankey-panel { flex: 0 0 auto; }

.tile-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1rem;
  flex: 0 0 auto;
}

.tile {
  background-color: $secondary-background;
  border-radius: 20px;
  padding: 1rem 1.1rem;

  .tile-label {
    font-family: 'Lexend';
    font-size: 0.7rem;
    color: $text;
    opacity: 0.5;
    margin: 0;
  }
  .tile-value {
    font-family: 'Inter';
    font-size: 1.6rem;
    color: $text;
    margin: 4px 0 0;
    line-height: 1.1;
    // placeholder dash is dimmed so an unfilled tile never reads as a zero.
    &.empty { opacity: 0.25; }
  }
  .tile-hint {
    font-family: 'Lexend';
    font-size: 0.65rem;
    color: $accent;
    opacity: 0.55;
    margin: 4px 0 0;
  }
}

// below ~1100px six tiles across becomes unreadable.
@media (max-width: 1100px) {
  .chart-row { grid-template-columns: 1fr; }
  .tile-row  { grid-template-columns: repeat(3, 1fr); }
}
</style>
