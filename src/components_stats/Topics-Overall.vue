<script setup lang="ts">
// ==========================================================================
//
// Topic mastery. The last section of docs/stats_page_design.md §7 to be built,
// and the first consumer of the 57,145 question tags seeded by
// scripts/buildTopics.ts.
//
// WHY NOT THE RADAR §2 PLANNED. The radar was chosen before the taxonomy
// existed, on the assumption that a subject has a handful of topics. It has
// 12 to 21 - a radar with twenty axes is a hairball, and its labels are long
// enough ("Atoms and radioactivity") to overrun the corners. Worse, the page's
// subject filter is a multiselect and topic sets are DISJOINT across subjects,
// so a radar spanning two subjects would draw a shape over axes that share no
// meaning. A bar sorted weakest-first answers the actual question - "what
// should I revise" - and reads the same whether one subject is selected or six.
//
// LOW N IS THE FAILURE MODE HERE. A topic with four questions behind it can sit
// at 25% on one unlucky guess. Rather than hide those rows, both panels put the
// question count in front of the reader: the bar labels carry it, and the
// scatter plots it as an axis with the threshold drawn on it. §6 asks for
// exactly that - "always render bucket counts so the reader can see the
// thinness".
// ==========================================================================
import { computed } from 'vue';
import { Layers, Microscope } from 'lucide-vue-next';
import EChart from './EChart.vue';
import { baseAxis, baseTooltip, type ChartTheme } from '@/lib/charts/echarts';
import { pct, count } from '@/lib/stats/format';
import { MODEL, Band, chanceLevel, isFading, type QueueItem } from '@/lib/stats/model';
import type { SubjectStatsView } from '@/lib/types/database';

// takes the RANKED topics rather than the raw mastery view, because the
// band, the retention and the marks all come from the model and re-deriving
// any of them here would put a second copy of the model in a template.
const props = defineProps<{
  ranked: QueueItem[];
  subjects: SubjectStatsView[];
}>();

// Past about fourteen rows the bars are thinner than their own labels. The
// count of what was left out is shown beside the panel rather than silently
// dropped - a truncated list that does not say it is truncated is a lie.
const MAX_BARS = 14;

const hasData = computed(() => props.ranked.length > 0);

// colour now carries the BAND, not the subject.
//
// The band is the actionable axis - mastered / worth practising / not yet
// established want three different verbs from the student, and that is the
// question this panel exists to answer. Subject is still available in the
// tooltip, and the page's own subject filter is the right way to split by it.
// Colouring by subject instead would spend the only pre-attentive channel the
// chart has on the dimension the reader already chose.
const BAND_COLOUR = (theme: ChartTheme): Record<Band, string> => ({
  [Band.Mastered]: theme.success,
  [Band.Proximal]: theme.series[0]!,
  [Band.Struggling]: theme.danger,
  [Band.Untested]: theme.muted,
});

const BAND_LABEL: Record<Band, string> = {
  [Band.Mastered]: 'Mastered',
  [Band.Proximal]: 'Worth practising',
  [Band.Struggling]: 'Not established',
  [Band.Untested]: 'Barely tested',
};

const bandCounts = computed(() => {
  const m = new Map<Band, number>();
  for (const t of props.ranked) m.set(t.reading.band, (m.get(t.reading.band) ?? 0) + 1);
  return m;
});

const subjectName = computed(() => {
  const m = new Map<string, string>();
  for (const s of props.subjects) m.set(s.subject_code, s.subject_name ?? s.subject_code);
  return m;
});

// Weakest first, by the point estimate. The chart is a picture of where the
// student stands; the ORDERING that says what to do about it is the queue in
// the Next steps section, which is a different question and a different sort.
const ranked = computed(() =>
  [...props.ranked].sort((a, b) => a.reading.accuracy.point - b.reading.accuracy.point));

const shown = computed(() => ranked.value.slice(0, MAX_BARS));
const hidden = computed(() => ranked.value.length - shown.value.length);

const MIN_Q = MODEL.queue.minQuestions;

const solid = computed(() => ranked.value.filter(t => t.reading.questions >= MIN_Q));

const weakest = computed(() => solid.value[0] ?? null);
const strongest = computed(() => solid.value[solid.value.length - 1] ?? null);

const spread = computed(() =>
  weakest.value && strongest.value && solid.value.length >= 2
    ? strongest.value.reading.accuracy.point - weakest.value.reading.accuracy.point
    : null);

// "fading" is the decay term from model.ts SS C surfaced directly. The
// test itself lives there - this file must not hold a number that decides
// anything about the student.
const fading = computed(() => ranked.value.filter(t => isFading(t.reading.retention)).length);

const tiles = computed(() => [
  {
    label: 'Worth practising',
    value: count(bandCounts.value.get(Band.Proximal) ?? 0),
    hint: 'cheapest marks are here',
  },
  {
    label: 'Mastered',
    value: count(bandCounts.value.get(Band.Mastered) ?? 0),
    // no single percentage here any more. The bar is the top grade the
    // PAPER can award and differs per paper - Core caps at C, Extended at A -
    // so naming one number would be wrong for most rows.
    hint: 'at the top grade the paper awards',
  },
  {
    label: 'Not established',
    value: count(bandCounts.value.get(Band.Struggling) ?? 0),
    hint: 'not yet above guessing',
  },
  {
    label: 'Fading',
    value: count(fading.value),
    hint: 'past their half-life',
  },
  {
    label: 'Spread',
    // Points, not a ratio: the gap between two percentages is a difference,
    // and writing it as "24%" invites reading it as a proportion of something.
    value: spread.value !== null ? `${Math.round(spread.value * 100)} pts` : null,
    hint: 'best topic minus worst',
  },
]);

const daysLabel = (d: number | null) =>
  d === null ? 'never practised' : d === 0 ? 'practised today' : `${d}d ago`;

// --------------------------------------------------------- weakest topics
// A horizontal bar per topic. ECharts stacks a category axis bottom-to-top, so
// the array is reversed: weakest first in the data means weakest at the top of
// the panel, which is where the eye starts.
const rankOption = (theme: ChartTheme) => {
  const rows = [...shown.value].reverse();
  const colour = BAND_COLOUR(theme);
  return {
    // 210px of gutter because these are syllabus topic names, not codes -
    // "Characteristics and classification of living organisms" is the label
    // Cambridge uses. At 172 the three longest were truncated to an ellipsis,
    // which on the row you are being told to revise is the wrong thing to cut.
    grid: { top: 8, right: 62, bottom: 24, left: 210 },
    tooltip: {
      ...baseTooltip(theme), trigger: 'item',
      formatter: (p: { dataIndex: number }) => {
        const t = rows[p.dataIndex]!;
        const r = t.reading;
        return `${t.topicName}<br/>${subjectName.value.get(t.subjectCode) ?? t.subjectCode}`
          + `<br/><b>${BAND_LABEL[r.band]}</b>`
          + `<br/>${pct(r.accuracy.point)} · ${r.marksAwarded}/${r.marksTotal} marks`
          + `<br/>${pct(r.accuracy.lower)}–${pct(r.accuracy.upper)} at 95% confidence`
          + `<br/>${r.questions} question${r.questions === 1 ? '' : 's'} · ${daysLabel(r.daysSincePractice)}`;
      },
    },
    xAxis: {
      type: 'value', min: 0, max: 1, ...baseAxis(theme),
      axisLabel: { ...baseAxis(theme).axisLabel, formatter: (v: number) => `${v * 100}%` },
      // The chance line. Everything left of it is indistinguishable from
      // guessing, which is the lower edge of the proximal region in model.ts.
      splitLine: { lineStyle: { color: theme.grid, width: 1 } },
    },
    yAxis: {
      type: 'category',
      data: rows.map(t => t.topicName),
      ...baseAxis(theme),
      splitLine: { show: false },
      axisLabel: {
        ...baseAxis(theme).axisLabel,
        fontSize: 11,
        width: 200,
        overflow: 'truncate',
      },
    },
    series: [{
      type: 'bar',
      barMaxWidth: 18,
      itemStyle: { borderRadius: [0, 4, 4, 0] },
      // The count rides on the bar's own label so the reader never has to
      // hover to find out how much is behind a number.
      label: {
        show: true, position: 'right', distance: 8, color: theme.text,
        fontFamily: theme.fontMono, fontSize: 11,
        formatter: (p: { dataIndex: number; value: number }) => {
          const r = rows[p.dataIndex]!.reading;
          return `${Math.round(p.value * 100)}%  ·  n=${r.questions}`;
        },
      },
      data: rows.map(t => ({
        value: t.reading.accuracy.point,
        itemStyle: {
          color: colour[t.reading.band],
          // Thin evidence is drawn hollow rather than hidden or recoloured:
          // it is not a worse score, it is a less certain one.
          opacity: t.reading.questions >= MIN_Q ? 1 : 0.45,
        },
      })),
      markLine: {
        silent: true, symbol: 'none',
        label: {
          color: theme.muted, fontFamily: theme.fontBody, fontSize: 9,
          formatter: 'chance', position: 'end',
        },
        lineStyle: { color: theme.axis, width: 1, type: 'dashed', opacity: 0.5 },
        data: [{ xAxis: chanceLevel(rows[0]?.reading.optionCount ?? 4) }],
      },
    }],
  };
};

// -------------------------------------------------------------- evidence
// Questions answered against accuracy, one point per topic. The whole purpose
// is the horizontal position: a topic in the bottom-LEFT is a bad sample, and a
// topic in the bottom-RIGHT is a confirmed gap. Reading a stats page as though
// those are the same thing is how a student ends up revising noise.
const evidenceOption = (theme: ChartTheme) => {
  const colour = BAND_COLOUR(theme);
  return {
    grid: { top: 16, right: 20, bottom: 36, left: 46 },
    tooltip: {
      ...baseTooltip(theme), trigger: 'item',
      formatter: (p: { data: { name: string; subject: string; band: string; value: number[] } }) =>
        `${p.data.name}<br/>${p.data.subject}<br/><b>${p.data.band}</b>`
        + `<br/>${(p.data.value[1]! * 100).toFixed(0)}% · ${p.data.value[0]} questions`,
    },
    xAxis: {
      type: 'value', min: 0, name: 'questions', nameLocation: 'middle', nameGap: 22,
      nameTextStyle: { color: theme.muted, fontFamily: theme.fontBody, fontSize: 10 },
      ...baseAxis(theme),
    },
    yAxis: {
      type: 'value', min: 0, max: 1, ...baseAxis(theme),
      axisLabel: { ...baseAxis(theme).axisLabel, formatter: (v: number) => `${v * 100}%` },
    },
    series: [{
      type: 'scatter',
      symbolSize: 11,
      data: ranked.value.map(t => ({
        name: t.topicName,
        subject: subjectName.value.get(t.subjectCode) ?? t.subjectCode,
        band: BAND_LABEL[t.reading.band],
        value: [t.reading.questions, t.reading.accuracy.point],
        itemStyle: {
          color: colour[t.reading.band],
          opacity: 0.8,
          borderWidth: 1,
          borderColor: theme.surface,
        },
      })),
      markLine: {
        silent: true, symbol: 'none',
        label: {
          color: theme.muted, fontFamily: theme.fontBody, fontSize: 10,
          formatter: `${MIN_Q} questions`,
        },
        lineStyle: { color: theme.axis, width: 1, type: 'dashed', opacity: 0.6 },
        // Everything left of this line is a sample, not a score.
        data: [{ xAxis: MIN_Q }],
      },
    }],
  };
};
</script>

<template>
  <div class="topics-layout">

    <div class="chart-row">
      <div class="panel rank-panel">
        <div class="panel-header">
          <Layers class="panel-icon" />
          <div>
            <h4>Topics, weakest first</h4>
            <p class="panel-sub">marks awarded against marks available, per syllabus topic</p>
          </div>
        </div>
        <EChart class="chart-canvas" :option="rankOption" :has-data="hasData" label="topic accuracy" />
        <!-- the legend explains the BANDS, because a band is a claim and
             a claim needs its rule stated. Each carries a word as well as a
             colour so it survives being read without colour vision. -->
        <p class="panel-legend">
          <span class="legend-item">
            <span class="swatch sw-struggling"></span> not above guessing
          </span>
          <span class="legend-item">
            <span class="swatch sw-proximal"></span> worth practising
          </span>
          <span class="legend-item">
            <span class="swatch sw-mastered"></span> at the paper's top grade
          </span>
          <span class="legend-item">
            <span class="swatch sw-untested"></span> under {{ MIN_Q }} questions
          </span>
          <span v-if="hidden > 0" class="legend-more">+{{ hidden }} more not shown</span>
        </p>
      </div>

      <div class="panel evidence-panel">
        <div class="panel-header">
          <Microscope class="panel-icon" />
          <div>
            <h4>How much is behind it</h4>
            <p class="panel-sub">a low score on four questions is not a weakness yet</p>
          </div>
        </div>
        <EChart class="chart-canvas" :option="evidenceOption" :has-data="hasData" label="topic accuracy against sample size" />
        <p class="panel-legend">
          left of the line: too few questions to read &nbsp;·&nbsp; bottom right: a real gap
        </p>
      </div>
    </div>

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
// the same column flow Focus uses - two charts and a metric bar do not fit
// the 20x20 grid the other two sections were drawn against.
.topics-layout {
  grid-column: 1 / 21;
  grid-row: 1 / 21;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

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

// the rank panel carries up to fourteen rows and the scatter one square, so
// they are not equal halves - a 14-row bar chart squeezed into 50% of the width
// truncates every label.
.chart-row {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 1rem;
  flex: 1 1 0;
  min-height: 0;
}

.chart-canvas {
  flex: 1 1 auto;
  // Taller than the other sections': fourteen categories need ~26px each
  // before the bars are thinner than the gaps between them.
  min-height: 420px;
  border-radius: 12px;
}
.evidence-panel .chart-canvas { min-height: 300px; }

.panel-legend {
  font-family: 'Lexend';
  font-size: 0.7rem;
  color: $text;
  opacity: 0.45;
  margin: 0.6rem 0 0;
  display: flex;
  align-items: center;
  column-gap: 14px;
  row-gap: 4px;
  flex-wrap: wrap;

  .legend-item { display: inline-flex; align-items: center; column-gap: 6px; }
  .swatch { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }
  .sw-struggling { background-color: $danger; }
  .sw-proximal   { background-color: var(--series-1); }
  .sw-mastered   { background-color: $success; }
  .sw-untested   { background-color: $muted; }
  .legend-more { opacity: 0.7; }
}

.tile-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
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
    // smaller than Focus's 1.6rem because two of these five tiles hold a
    // topic NAME, not a number - "Atoms and radioactivity" at 1.6rem runs to
    // three lines and pushes the hint out of the tile.
    font-size: 1.15rem;
    color: $text;
    margin: 4px 0 0;
    line-height: 1.2;
    overflow-wrap: anywhere;
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

@media (max-width: 1100px) {
  .chart-row { grid-template-columns: 1fr; }
  .tile-row  { grid-template-columns: repeat(3, 1fr); }
}
</style>
