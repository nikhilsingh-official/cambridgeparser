<!-- ==========================================================================
     Documentation only. Third in the series: database_design.md specifies what
     is stored, future_work.md tracks what is missing, this one specifies how
     the stored data becomes the stats page.
     ========================================================================== -->

# SmartSolver — Stats Page Design

Maps every recorded field to a visual, picks a charting library, and fills the
slots already laid out in `components_stats/`.

---

## 0. Decisions taken

### 0.1 Accuracy is **marks awarded / marks total** — DECIDED

Everywhere. It is the exam-realistic number: an unanswered question counts
against you, exactly as it would in the real paper.

This previously disagreed with itself. `v_attempt_summary.accuracy` was
`avg((qa.is_correct)::int)`; Postgres `avg` skips nulls and `is_correct` is null
for unanswered questions, so it was really correct ÷ **answered**. The end screen
has always divided by the full paper. The same attempt could read 60% on one
screen and 80% on the other.

`v_attempt_summary`, `v_subject_stats` and `v_topic_mastery` are now all
marks-based and agree with the end screen by construction. The old ratio survives
as `precision_when_answered` — "when you commit, how often are you right" — which
is a real question, just not the headline.

Subject-level accuracy is **marks-weighted**, not the mean of per-paper
percentages, so a 10-mark paper does not count as much as a 40-mark one.

### 0.2 Confidence stays behavioural — DECIDED

`question_metrics.confidence` is a weighted composite of time, eliminations,
review marks and revisits, rather than a value the student states.

Kept deliberately, and the reasoning is sound: a confidence prompt is only
accurate if it is answered honestly every time, and in practice students
optimising for accuracy dismiss it. A dismissed or reflexively-tapped prompt is
worse than a behavioural estimate, because it *looks* like ground truth. The
inferred metric costs the student nothing and is never skipped.

Two consequences to hold onto:
- **Label it "behavioural confidence"** in the UI. The calibration chart is
  answering "does hesitation predict being wrong?" — which is genuinely useful,
  and is not the same claim as classical calibration. Say what it measures.
- It is **weight-dependent**, which is exactly why `question_metrics` is
  versioned by `metrics_version`. Retuning the weights in `enrichAnalytics.ts`
  without inserting a new version silently makes old and new attempts
  incomparable on this axis. See `future_work.md` §6.4.

### 0.3 Two view bugs fixed while settling the above

`v_daily_activity.total_time_ms` and `v_subject_stats.total_time_ms` were
`sum(ea.duration_ms)` computed across a join to `question_attempts`, so each
attempt's duration was summed once **per question** — roughly 40x the real study
time on a 40-question paper. `count(distinct ea.id)` next to it was correct,
which is what hid it. Both views now aggregate the two grains separately.

Worth noting because the engagement section is largely built on these two
columns; unfixed, it would have reported ~26-hour study days.

## 1. What is recorded

Grain determines chart type more than anything else, so the inventory is grouped
by it.

### Per attempt — `exam_attempts` / `v_attempt_summary`
| Field | Type |
|---|---|
| `paper_id` → `subject_code`, `series`, `exam_year`, `paper_number`, `variant` | categorical |
| `status` | enum: in_progress / completed / abandoned |
| `started_at`, `finished_at`, `local_date`, `client_timezone` | temporal |
| `duration_ms` | continuous |
| `questions_total`, `questions_answered`, `questions_correct`, `accuracy` | count / ratio |
| `avg_time_per_question_ms` | continuous |
| `metrics_version` | provenance, never plotted |

### Per question — `question_attempts`
| Field | Type | Notes |
|---|---|---|
| `selected_option`, `correct_option` | categorical 0–7 | the A/B/C/D pair |
| `is_correct` | boolean, nullable | null = unanswered |
| `eliminated_mask` | bitfield | which options were ruled out |
| `time_spent_ms` | continuous, heavy right tail | **use median, not mean** |
| `hesitation_ms` | continuous, nullable | time to first action |
| `option_switch_count`, `elimination_reversal_count`, `revisit_count` | small counts | mostly 0–3 |
| `marked_for_review_count`, `marked_as_difficult_count`, `marked_for_save_count` | small counts | |
| `stable_elimination_ratio` | 0–1 | |
| `exploration_depth`, `exploration_breadth` | small counts | |

### Per question, versioned — `question_metrics`
`confidence`, `difficulty`, `interest` — all 0–1, all weight-dependent.

### Raw stream — `attempt_events`
`seq`, `question_number`, `element_type`, `action_type`, `option_index`,
`elapsed_ms`, `occurred_at`. The only source for **ordering** and **transition
type**. Everything in §5 depends on it.

### Derived views
`v_question_flags` (is_guess / is_overconfident / is_underconfident),
`v_calibration_curve`, `v_daily_activity`, `v_hour_of_day`, `v_subject_stats`,
`v_topic_mastery`.

---

## 2. Library choice — **Apache ECharts**

### The comparison that matters

The deciding question is not "which library draws a line chart" — they all do.
It is **which chart types this dataset needs, and which are first-class**.

| Needed visual | ECharts | Chart.js | D3 |
|---|---|---|---|
| Calendar heatmap (daily activity) | **`calendar` coordinate system, built in** | `chartjs-chart-matrix` plugin + manual date grid | hand-built, ~80 lines |
| Sankey (answer changes) | **built in** | none | `d3-sankey` + all rendering |
| Radar (topic mastery) | built in | built in | hand-built |
| Boxplot (time distributions) | **built in** | `chartjs-chart-boxplot` plugin | hand-built |
| Polar bar (hour of day) | **built in** | partial (`polarArea`, less control) | hand-built |
| Scatter, 40k+ points | **canvas, `large: true`** | canvas, fine | SVG chokes; needs canvas by hand |
| Linked zoom across charts | **`dataZoom`, declarative** | plugin + manual sync | manual |
| Sunburst (qualification → subject) | **built in** | none | `d3-hierarchy` |

Chart.js loses on five of nine — each one becoming a plugin hunt or a bespoke
build. D3 wins on flexibility and loses on every hour spent reimplementing what
ECharts ships.

**Recommendation: ECharts for all of it.** Not because it is the most powerful
option in the abstract, but because the specific charts this schema earns —
calendar heatmap, sankey, boxplot, polar — are exactly its strong suit.

### Bundle discipline is non-negotiable here

`future_work.md` §5 already flags a **1.4 MB single JS chunk**. Importing
ECharts wholesale adds ~1 MB and roughly doubles the problem. Always tree-shake:

```ts
// never `import * as echarts from 'echarts'` — that is the full ~1MB build.
import * as echarts from 'echarts/core';
import { LineChart, BarChart, PieChart, HeatmapChart,
         ScatterChart, SankeyChart, RadarChart, BoxplotChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent, CalendarComponent,
         DataZoomComponent, MarkLineComponent, VisualMapComponent,
         PolarComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([ /* only what this page uses */ ]);
```

Tree-shaken, the set above is ~300–400 kB raw / ~110 kB gzipped. Load the whole
stats route behind `import()` so a student who never opens stats never pays.

### Vue integration: a local composable, not `vue-echarts`

`vue-echarts` is fine, but it is a dependency to wrap ~30 lines. A local
`useChart()` keeps control and adds nothing to `package.json`:

```ts
// src/composables/useChart.ts
export function useChart(el: Ref<HTMLElement | null>, option: Ref<EChartsOption>) {
  let chart: echarts.ECharts | null = null;
  let ro: ResizeObserver | null = null;

  onMounted(() => {
    if (!el.value) return;
    chart = echarts.init(el.value, 'smartsolver');   // registered theme, §2.1
    chart.setOption(option.value);
    // ECharts does not resize itself; the stats grid is fluid, so it must.
    ro = new ResizeObserver(() => chart?.resize());
    ro.observe(el.value);
  });

  // notMerge false so partial option updates (new data, same axes) are cheap.
  watch(option, v => chart?.setOption(v), { deep: true });
  onBeforeUnmount(() => { ro?.disconnect(); chart?.dispose(); });
}
```

### 2.1 Theme: one source of truth, not two

The palette lives in `styles/_variables.scss`. JS cannot read SCSS variables, so
hardcoding hexes into a chart theme creates a second palette that will drift the
first time a colour changes.

Export them as CSS custom properties once, and read them at theme-registration
time:

```scss
// styles/main.scss — makes the SCSS palette readable from JS.
:root {
  --accent: #{$accent};
  --secondary-color: #{$secondary-color};
  --success: #{$success};
  --warning: #{$warning};
  --danger: #{$danger};
  --text: #{$text};
  --secondary-background: #{$secondary-background};
}
```

```ts
// read once at startup, register as an ECharts theme so every chart on the
// page inherits it and no component sets colours itself.
const css = getComputedStyle(document.documentElement);
const t = (n: string) => css.getPropertyValue(n).trim();
echarts.registerTheme('smartsolver', {
  backgroundColor: 'transparent',        // the card already paints $secondary-background
  textStyle: { fontFamily: 'Lexend', color: t('--text') },
  color: [t('--accent'), t('--secondary-color'), t('--success'),
          t('--warning'), t('--danger')],
});
```

**Semantic colours are fixed, categorical colours rotate.** Correct is always
`$success`, incorrect always `$danger`, unanswered always muted — never let the
palette rotation assign those. Subjects may take any hue.

---

## 3. Slot-by-slot mapping

Your existing layout in `Progress-Overall.vue` / `Engagement-Overall.vue` /
`Focus-Overall.vue` already names the slots. Filling them as-is where the data
suits, flagged where it does not.

### Header — `.pie-container` (1:1 square, currently empty)

**Sunburst: qualification → subject → paper count.** ECharts `sunburst`.
A square slot with a hierarchy is exactly its case, and it answers "what am I
actually spending my practice on" at a glance. Click a ring to filter the whole
page — the sunburst doubles as the primary filter control alongside your three
multiselects.

### Section 1 — PROGRESS

| Slot | Chart | Series | Source |
|---|---|---|---|
| `.multi-line-container` (largest) | **Multi-series line, score over time** | one line per subject, x = `local_date`, y = score | `v_attempt_summary` |
| `.progress-line-container` (wide, short) | **Accuracy-per-paper column chart**, coloured by subject, doubling as the `dataZoom` controller for the multiline above | x = attempt, y = score | `v_attempt_summary` |
| `.donut-container` | **Outcome donut**: correct / incorrect / unanswered, with **lucky guesses carved out of correct** as a separate slice | centre label = score % | `v_attempt_summary` + `v_question_flags` |
| 7 × `.quickview-container` | `TotalPapersSolved`, `OverallAccuracy`, `StrongestSubject`, `MostImprovedSubject`, `ImprovementRate`, `FastestCompletionTime`, `ThisWeeksAccuracy` | number + sparkline | `StatCategory` already defines all of these |

Two details on the multiline:
- **Show the points.** With 4 attempts a smooth line implies a trend that isn't
  there. `symbol: 'circle', symbolSize: 6, smooth: false`.
- **Draw the goal.** `goals.kind = 'accuracy_target'` → a `markLine` at that y.
  It is the only thing on this page that turns a chart into a target.

### Section 2 — ENGAGEMENT

| Slot | Chart | Notes |
|---|---|---|
| `.heatmap-container` | **Calendar heatmap** — ECharts `calendar` + `heatmap`, GitHub-contributions style | `v_daily_activity`. Colour by `questions`, not `papers` — papers is too coarse (most days are 0 or 1) |
| `.session-line-container` | **Study minutes per day, area line** with `dataZoom` | `v_daily_activity.total_time_ms` |
| `.session-log` (tall, narrow, left) | **Not a chart.** Scrollable recent-attempts list: paper id, date, score, duration, one inline sparkline per row | `v_attempt_summary` ordered by `finished_at` |
| 4 × `.quickview-container` | `PracticeStreak`, `LongestSession`, `PeakSolvingHour`, `TimeSinceLastPaper` | |

**`PeakSolvingHour` deserves better than a number.** `v_hour_of_day` is 24 bins
of cyclical data — a **polar bar chart** (ECharts `polar` + `angleAxis` of 24)
reads instantly as a clock face and shows the *shape* of when you work, not just
the argmax. If a quickview tile is too small, promote it into the section.

### Section 3 — FOCUS *(redesigned — see §3.1)*

The original layout put a tall `focus-pie-container` plus six tiles in
**columns 1–7 only**, leaving roughly 70% of the section's width empty, and four
of its ten tiles shared the class `quickview-container-1`, so they stacked in a
single cell. It was the least-finished section, and it is also where the two
most insight-dense charts in the dataset belong — neither of which is a pie.

Redesigned below. The original is preserved at tag `stats-page-original`.

### 3.1 Focus — final layout

Dropped the fixed 20×20 grid here for a **flow of rows**, because this section's
content is naturally two big charts plus a metric bar, and forcing that into
20 equal rows only makes the sizes arbitrary. Progress and Engagement keep their
grids; they suit them.

```
┌───────────────────────────────────────────────────────────┐
│  CALIBRATION CURVE            │  TIME vs CORRECTNESS       │   row 1
│  behavioural confidence       │  scatter, log x            │   (2 cols)
│  vs observed accuracy         │  guesses cluster ↙         │
│  y=x diagonal + bucket counts │  overthinking ↗            │
├───────────────────────────────────────────────────────────┤
│  ANSWER-CHANGE SANKEY                                      │   row 2
│  first choice → final choice, split right/wrong            │   (full width)
├───────────────────────────────────────────────────────────┤
│ over- │ under- │ guess │ guess │ elim.  │ mean            │   row 3
│ conf. │ conf.  │ count │ acc.  │ precis.│ hesitation      │   (6 tiles)
└───────────────────────────────────────────────────────────┘
```

| Panel | Chart | Source |
|---|---|---|
| Calibration curve | ECharts `line` + `markLine` diagonal, faint `bar` behind for bucket counts | `v_calibration_curve` |
| Time vs correctness | ECharts `scatter`, x = `time_spent_ms` (log), y = `confidence`, colour = `is_correct`, size = `exploration_depth` | `question_attempts` + `question_metrics` |
| Answer-change sankey | ECharts `sankey` | `attempt_events` (§5) |
| 6 tiles | plain numbers | `v_question_flags` |

Why these two charts carry the section:
- The **calibration curve** is the only view that says something about the
  student rather than the score. Above the diagonal = underconfident (you know
  more than you think), below = overconfident (the dangerous direction).
- The **scatter** puts two different failure modes on one pair of axes: fast +
  low-confidence + wrong is guessing, slow + high-confidence + wrong is a
  misconception. They need opposite remedies, and no single number separates them.

The sankey is placed but **renders empty until the query layer reads
`attempt_events`** (§5). Give it the low-n empty state from §6 rather than a
blank card.

## 4. What should *not* be a chart

Worth stating, because a stats page fails more often from clutter than from
missing charts.

- **`metrics_version`** — provenance. Show as a footnote when comparing across
  versions, never as a series.
- **`stable_elimination_ratio`, `exploration_breadth`** — intermediate inputs to
  `confidence`/`difficulty`. Plotting both the inputs and the composite invites
  the reader to double-count. Keep them in a per-question detail drawer.
- **`option_switch_count` alone** — a count of switches with no direction is
  close to meaningless. It becomes valuable only as §5's sankey.
- **Per-question `revisit_count` as its own chart** — fold it into the scatter's
  tooltip.

---

## 5. The charts that need `attempt_events` (highest value, not yet buildable)

`future_work.md` §4 calls answer-change quality "the highest-value unbuilt
metric". Now that the event stream persists, these become possible — they need a
query layer, not new recording.

**Answer-change Sankey.** `action_type` already distinguishes `setCorrect`,
`elimToCorrect`, `correctToElim`, `deselectedCorrect`, `setElim`,
`deselectedElim` with the option index. Flow: *first selection* → *final
selection*, split by whether each was right. Answers the question every student
asks — **"should I trust my first instinct?"** — with their own data. ECharts
`sankey`.

**Pacing / fatigue curve.** `elapsed_ms` gives true answering order, which
`question_number` cannot (students skip around). Line of time-per-question
against answering *position*, with a trend `markLine`. Reveals whether accuracy
decays through a paper.

**Elimination precision.** `eliminated_mask` × `correct_option`: how often a
ruled-out option really was wrong, and — the interesting half — how often the
*correct* answer got eliminated. A single gauge plus a "you eliminated the right
answer on N questions" list.

---

## 6. Empty and low-n states

Most of these charts are noise or an outright lie at small n, and a stats page
that looks broken on day one is worse than one with fewer charts.

| Chart | Minimum to be meaningful | Below that |
|---|---|---|
| Multiline trend | 3 attempts per subject | show points only, no connecting line |
| Calibration curve | ~200 answered questions | **10 deciles is far too many** — `v_calibration_curve` uses `width_bucket(…, 10)`, so at 40 questions most buckets hold ≤4 and the curve is pure noise. Drop to 4–5 buckets until n is large, and always render bucket counts so the reader can see the thinness |
| Calendar heatmap | any | fine when empty — an empty year still reads correctly |
| Boxplots | 5 attempts per subject | fall back to a dot strip |
| Topic mastery | the paper is tagged in `question_topics` | hide the section entirely; do not show an empty radar |
| Sankey | ~20 answer changes | hide |

Give every chart an explicit empty state naming what to do — *"Sit two more
papers to see a trend"* — not a blank card.

---

## 7. Build order

1. ~~Settle §0.1~~ — **done**, accuracy is marks/total everywhere (§0).
2. **Query layer.** `src/lib/supabase/queries/` — the app still performs zero
   reads (`future_work.md` §2.3). Typed against `database.ts`, one function per
   view. Nothing below is possible first.
3. **Chart plumbing.** `useChart()`, the CSS-variable theme, the tree-shaken
   ECharts entry point, route-level `import()`.
4. **Progress section.** Multiline + column + donut. Highest value per unit of
   work, and it validates the plumbing on ordinary chart types.
5. **Engagement section.** Calendar heatmap, session line, attempts list.
6. **Focus section.** Calibration curve + scatter. Do these *after* enough real
   attempts exist to tune the thresholds in §6 against actual data.
7. **§5 event charts.** Sankey, pacing, elimination precision.
8. **Topic mastery.** Data is in (`question_topics`); nothing renders it yet.

---

## 8. Dependency to add

```bash
npm i echarts        # ~1MB installed; ~110kB gzipped when tree-shaken per §2
```

Nothing else. No `vue-echarts` (§2), no D3 (ECharts covers every chart above),
no Chart.js. `cytoscape` is already installed for graph work and is unrelated —
do not press it into charting.
