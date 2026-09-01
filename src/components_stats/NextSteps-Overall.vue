<script setup lang="ts">
// ==========================================================================
//
// Next steps - the only section on this page that ends in a verb.
//
// Jivet et al. (2020) found that only ~17% of learning dashboards offer any
// decision support at all, and that awareness without it does not change
// behaviour: "checking a learning dashboard regularly without making any
// changes in your learning behaviour will not lead to better outcomes."
// Everything below Progress on this page tells the student what happened.
// This section tells them what to do next, and why.
//
// THIS COMPONENT COMPUTES NOTHING. Every number, ranking, band and threshold
// comes from src/lib/stats/model.ts. If a rule needs changing it changes there
// and this file re-renders. See docs/solver/stats_priority.md for the evidence
// behind picking these three panels over anything else.
// ==========================================================================
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { ListChecks, Target, RotateCcw } from 'lucide-vue-next';
import { MODEL, Band, type QueueItem, type MissedQuestion, type Readiness } from '@/lib/stats/model';

import { pct, subjectLabel } from '@/lib/stats/format';

const props = defineProps<{
  queue: QueueItem[];
  missed: MissedQuestion[];
  readiness: (Readiness & {
    key: string; subjectCode: string; subjectName: string; paperNumber: number | null;
  })[];
}>();

/** How many missed questions to list. The rest are counted, not hidden. */
const MISSED_SHOWN = 8;

// 0478 and 9618 are both "Computer Science", and this panel lists them one
// above the other with different grades. subjectLabel appends the code only
// where the name is actually ambiguous in what is on screen.
//
// The paper number is always shown: thresholds are per component, IGCSE Paper 1
// is Core and cannot award above a C, and a row reading just "Physics · C" hides
// the difference between a Core ceiling and an Extended shortfall.
const graded = computed(() => {
  const all = props.readiness.map(r => ({
    subject_code: r.subjectCode, subject_name: r.subjectName,
  }));
  return props.readiness.map((r, i) => ({
    ...r,
    label: subjectLabel(all[i]!, all)
      + (r.paperNumber === null ? '' : ` · Paper ${r.paperNumber}`),
  }));
});

const shownMissed = computed(() => props.missed.slice(0, MISSED_SHOWN));
const moreMissed = computed(() => Math.max(0, props.missed.length - MISSED_SHOWN));

// The band decides the verb. A struggling topic and a proximal one both look
// like "you are bad at this" on a chart and need opposite advice - practice
// for one, teaching for the other. See model.ts SS D.
const BAND_COPY: Record<Band, { label: string; verb: string }> = {
  [Band.Mastered]: { label: 'Mastered', verb: 'keep it warm' },
  [Band.Proximal]: { label: 'Worth practising', verb: 'practise this' },
  [Band.Struggling]: { label: 'Not established', verb: 'learn it first' },
  [Band.Untested]: { label: 'Barely tested', verb: 'sit more of it' },
};

// Why this item is in the queue, from the term that contributed most. The
// ranking is a weighted sum and an unexplained ranking is one a student is
// entitled to ignore - Jivet's "transparency of design".
const REASON: Record<QueueItem['driver'], string> = {
  gap: 'biggest gain per question',
  decay: 'fading since you last practised',
  marks: 'carries the most marks',
};

function staleness(item: QueueItem): string {
  const d = item.reading.daysSincePractice;
  if (d === null) return 'never practised';
  if (d === 0) return 'practised today';
  return `${d} day${d === 1 ? '' : 's'} ago`;
}
</script>

<template>
  <div class="next-layout">
    <div class="chart-row">

      <!-- ------------------------------------------------ revision queue -->
      <div class="panel queue-panel">
        <div class="panel-header">
          <ListChecks class="panel-icon" />
          <div>
            <h4>Practise these next</h4>
            <p class="panel-sub">
              ranked by how much a question is worth to you right now, not by how bad the score is
            </p>
          </div>
        </div>

        <ol v-if="queue.length" class="queue">
          <li v-for="(item, i) in queue" :key="item.topicId" class="queue-item">
            <span class="queue-rank">{{ i + 1 }}</span>
            <div class="queue-body">
              <div class="queue-title">
                <span class="queue-topic">{{ item.topicName }}</span>
                <span class="queue-band" :class="`band-${item.reading.band}`">
                  {{ BAND_COPY[item.reading.band].label }}
                </span>
              </div>
              <div class="queue-meta">
                {{ BAND_COPY[item.reading.band].verb }}
                &nbsp;·&nbsp; {{ REASON[item.driver] }}
                &nbsp;·&nbsp; {{ staleness(item) }}
                <template v-if="item.reading.questions >= MODEL.queue.minQuestions">
                  &nbsp;·&nbsp; {{ pct(item.reading.accuracy.point) }} of {{ item.reading.questions }}
                </template>
                <template v-else>
                  &nbsp;·&nbsp; only {{ item.reading.questions }} questions so far
                </template>
              </div>
              <!-- The score bar is the weighted sum, drawn as its three terms
                   so the ranking can be read rather than trusted. -->
              <div class="queue-bar" :aria-label="`priority ${Math.round(item.score * 100)}%`">
                <span class="seg seg-gap" :style="{ width: `${item.terms.gap * 100}%` }" />
                <span class="seg seg-decay" :style="{ width: `${item.terms.decay * 100}%` }" />
                <span class="seg seg-marks" :style="{ width: `${item.terms.marks * 100}%` }" />
              </div>
            </div>
          </li>
        </ol>
        <p v-else class="empty">Nothing to recommend yet — sit a topic-tagged paper first.</p>

        <p class="panel-legend">
          <span class="swatch seg-gap" /> room to improve
          <span class="swatch seg-decay" /> fading
          <span class="swatch seg-marks" /> marks at stake
        </p>
      </div>

      <!-- ---------------------------------------------------- readiness -->
      <div class="panel readiness-panel">
        <div class="panel-header">
          <Target class="panel-icon" />
          <div>
            <h4>Where you'd land today</h4>
            <!-- The caveat is not small print. This is a component grade,
                 not a qualification grade. The average is the right scale
                 HERE specifically, because each row pools several sessions -
                 a single paper's summary uses that paper's own boundary
                 instead. See model.ts SS F. -->
            <p class="panel-sub">
              one component, pooled across your papers and measured against
              Cambridge's published thresholds averaged over those sessions —
              not your final grade
            </p>
          </div>
        </div>

        <ul v-if="readiness.length" class="grades">
          <li v-for="r in graded" :key="r.key" class="grade-row">
            <div class="grade-left">
              <span class="grade-subject">{{ r.label }}</span>
              <span class="grade-detail">
                {{ pct(r.accuracy.point) }} · {{ r.marksAwarded }}/{{ r.marksTotal }} marks
              </span>
            </div>
            <div class="grade-right" :class="{ unreliable: !r.reliable }">
              <span class="grade-letter">{{ r.reliable ? r.grade : '—' }}</span>
              <span class="grade-range">
                <template v-if="r.reliable">
                  {{ r.best === r.worst ? 'firm' : `${r.best}–${r.worst}` }}
                </template>
                <template v-else-if="!r.thresholds">
                  no published thresholds
                </template>
                <template v-else>
                  needs {{ MODEL.grade.minQuestions }}+ questions
                </template>
              </span>
            </div>
          </li>
        </ul>
        <p v-else class="empty">No completed papers in this selection.</p>

        <!-- Two different uncertainties, and they are not the same thing:
             how well we know this student, and how much the boundary itself
             moves between sessions. Saying only the first would imply the
             second is fixed. -->
        <p class="panel-legend">
          the range is the 80% interval on your marks — and the boundaries
          themselves move a few marks every session
        </p>
      </div>
    </div>

    <!-- -------------------------------------------------- wrong answers -->
    <div class="panel missed-panel">
      <div class="panel-header">
        <RotateCcw class="panel-icon" />
        <div>
          <h4>Redo these questions</h4>
          <p class="panel-sub">
            every question you got wrong, hardest-working topic first — retrieval practice is
            the highest-utility revision technique there is
          </p>
        </div>
      </div>

      <ul v-if="shownMissed.length" class="missed">
        <li v-for="m in shownMissed" :key="`${m.paperId}#${m.questionNumber}`" class="missed-item">
          <RouterLink class="missed-link" :to="`/solver/${m.paperId}`">
            {{ m.paperId }} <span class="missed-q">Q{{ m.questionNumber }}</span>
          </RouterLink>
          <span class="missed-topic">{{ m.topicName }}</span>
        </li>
      </ul>
      <p v-else class="empty">No wrong answers in this selection. Sit a harder paper.</p>

      <p v-if="moreMissed" class="panel-legend">
        +{{ moreMissed }} more · a generated re-practice paper is the next step for this panel
      </p>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.next-layout {
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
  margin-bottom: 0.9rem;

  h4 { font-family: 'Inter'; font-weight: 400; color: $text; margin: 0; font-size: 1.05rem; }
  .panel-sub {
    font-family: 'Lexend'; font-size: 0.75rem; color: $text;
    opacity: 0.45; margin: 2px 0 0; max-width: 56ch;
  }
  .panel-icon { width: 22px; height: 22px; color: $accent; flex-shrink: 0; margin-top: 2px; }
}

// the queue is the point of the section, so it gets the wider column.
.chart-row {
  display: grid;
  grid-template-columns: 3fr 2fr;
  // `start`, not the default `stretch`. The two panels hold unrelated
  // amounts of content - six queue entries against one line per subject - and
  // stretching left the readiness card two-thirds empty.
  align-items: start;
  gap: 1rem;
  flex: 1 1 0;
  min-height: 0;
}

.empty {
  font-family: 'Lexend'; font-size: 0.8rem; color: $text; opacity: 0.4;
  margin: 0.5rem 0; text-align: center; padding: 1.5rem 0;
}

// ------------------------------------------------------------------ queue
.queue { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.85rem; }

.queue-item { display: flex; align-items: flex-start; column-gap: 0.85rem; }

.queue-rank {
  flex: 0 0 auto;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: $accent;
  opacity: 0.7;
  width: 1.2rem;
  text-align: right;
  line-height: 1.4;
}

.queue-body { flex: 1 1 auto; min-width: 0; }

.queue-title { display: flex; align-items: baseline; column-gap: 0.6rem; flex-wrap: wrap; }
.queue-topic { font-family: 'Inter'; font-size: 0.92rem; color: $text; }

.queue-band {
  font-family: 'Lexend';
  font-size: 0.6rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid currentColor;
  opacity: 0.85;
}
// Never colour alone: each band carries a word as well as a hue.
.band-mastered    { color: $success; }
.band-proximal    { color: $accent; }
.band-struggling  { color: $danger; }
.band-untested    { color: $text; opacity: 0.45; }

.queue-meta {
  font-family: 'Lexend';
  font-size: 0.68rem;
  color: $text;
  opacity: 0.45;
  margin-top: 2px;
}

.queue-bar {
  display: flex;
  height: 4px;
  margin-top: 6px;
  border-radius: 2px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.05);
  .seg { display: block; height: 100%; }
}
.seg-gap   { background-color: $accent; }
.seg-decay { background-color: $warning; }
.seg-marks { background-color: $success; }

.panel-legend {
  font-family: 'Lexend';
  font-size: 0.68rem;
  color: $text;
  opacity: 0.4;
  margin: 0.9rem 0 0;
  display: flex;
  align-items: center;
  column-gap: 6px;
  flex-wrap: wrap;

  .swatch {
    width: 8px; height: 8px; border-radius: 2px; display: inline-block;
    margin-left: 8px;
    &:first-child { margin-left: 0; }
  }
}

// -------------------------------------------------------------- readiness
.grades { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.9rem; }

.grade-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  column-gap: 1rem;
}

.grade-left { min-width: 0; }
.grade-subject { display: block; font-family: 'Inter'; font-size: 0.92rem; color: $text; }
.grade-detail { display: block; font-family: 'Lexend'; font-size: 0.68rem; color: $text; opacity: 0.45; }

.grade-right { text-align: right; flex: 0 0 auto; }
.grade-letter {
  display: block;
  font-family: var(--font-mono);
  font-size: 1.6rem;
  line-height: 1.1;
  color: $accent;
}
.grade-range { display: block; font-family: 'Lexend'; font-size: 0.65rem; color: $text; opacity: 0.45; }
// an unreliable estimate is dimmed AND shows an em dash rather than a
// letter. A grade off twelve questions is not a smaller claim, it is a wrong one.
.grade-right.unreliable .grade-letter { color: $text; opacity: 0.25; }

// ----------------------------------------------------------------- missed
.missed-panel { flex: 0 0 auto; }

.missed {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.6rem 1rem;
}

.missed-item { display: flex; flex-direction: column; min-width: 0; }

.missed-link {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: $accent;
  text-decoration: none;
  &:hover { text-decoration: underline; }
  .missed-q { opacity: 0.7; }
}

.missed-topic {
  font-family: 'Lexend';
  font-size: 0.66rem;
  color: $text;
  opacity: 0.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .chart-row { grid-template-columns: 1fr; }
}
</style>
