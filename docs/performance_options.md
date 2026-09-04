<!--

This is a decision document, not an implementation. Measurements describe the
repository state inspected on 2026-09-04; remeasure after changing dependencies.
-->

# CP-016, CP-018 and CP-019: options and recommendations

## Implementation status — 2026-09-04

- **CP-016 implemented locally:** `fetch-pdf` now returns one multipart response
  containing a binary PDF and JSON metadata. A live local Edge invocation of
  `9700_w25_13` returned all 2,006,131 PDF bytes and 40 answers with 4,093 bytes
  of multipart overhead; the installed Supabase Functions client decoded it.
  A real Chromium solver session decoded the response from the local Edge
  runtime and loaded the paper successfully. Hosted-gateway and wider
  browser-matrix verification remain part of CP-011/CP-014.
- **CP-019 low-risk cleanup implemented:** the expression-free light canvas
  player removes the Lottie `eval` warning, `vue3-lottie` is removed, and unused
  ECharts registrations are gone. The production chunks are now 203.8 KiB raw /
  56.2 KiB gzip for Lottie and 635.0 / 215.1 KiB for ECharts. Vite's generic
  ECharts size warning remains; viewport deferral is measurement-dependent.
- **CP-021 forward calculation fixed:** explicit Star, Save, and review intent
  now run in the documented direction and have a monotonicity regression test.
  Existing version-1 persisted composites were not backfilled.

## Original recommended order

1. **CP-018 correctness first:** fix and test the inverted `Star`, `Save`, and
   interest-from-`Flag` signals before treating the derived metrics as useful.
2. **CP-019 low-risk cleanup:** use Lottie's light canvas build, remove the unused
   `vue3-lottie` dependency, and prune three unused ECharts registrations.
3. **CP-016 transport:** replace the PDF JSON number array with a multipart
   response, subject to a browser/gateway smoke test. Retain a length-prefixed
   binary envelope as the compatibility fallback.
4. Defer Storage caching and viewport-loaded charts until production measurements
   show repeated PDF fetches or Stats startup are material costs.

## CP-016 — PDF response inflation

### Baseline before the transport change

Before CP-016, [`fetch-pdf`](../supabase/functions/fetch-pdf/index.ts) downloaded
the question and mark-scheme PDFs, parsed and persisted the answer key, then
serialized the question paper as `Array.from(new Uint8Array(qpArrayBuffer))`
inside JSON. The client turned that number array back into a `Uint8Array`, `Blob`,
and object URL. The same response also carried the full extracted rows (including
PDF geometry) and persistence status, so returning only raw PDF bytes was not a
drop-in replacement.

The largest checked golden-corpus PDF was **2,006,131 bytes**. Measured encodings:

| Encoding | Encoded bytes | Relative to PDF | Gzip bytes |
|---|---:|---:|---:|
| Raw PDF | 2,006,131 | 1.00x | — |
| JSON number array | 7,164,768 | 3.57x | 2,546,624 |
| Base64 text | 2,674,853 | 1.33x | 2,000,646 |

Base64's baseline expansion follows directly from encoding each 24 input bits as
four six-bit characters; padding handles the final partial group
([RFC 4648 §4](https://datatracker.ietf.org/doc/html/rfc4648#section-4)). It is a
substantial improvement over this number array, but still adds conversion work and
avoidable bytes compared with transporting binary.

### Options, ranked

| Rank | Design | Requests per open | Cost/load character | Main trade-off |
|---:|---|---:|---|---|
| 1 | `multipart/form-data`: PDF `Blob` plus compact JSON metadata | 1 Edge invocation | Removes array stringify/parse and preserves the current one-call contract | Must verify `Response.formData()` in supported browsers and through the hosted gateway |
| 2 | Length-prefixed binary envelope: 4-byte metadata length, UTF-8 JSON, then PDF | 1 Edge invocation | Same wire benefit and broad `ArrayBuffer`/`TextDecoder` support | Small custom protocol and an extra buffer copy |
| 3 | Raw `application/pdf` plus a separate answer-key query | 1 Edge + 1 database request | Simplest body and native `Blob` result | Current database rows do not carry all extracted geometry; changes fallback/error semantics |
| 4 | Storage object URL plus compact JSON | Edge + Storage GET on a cold/open path | Best route to persistent CDN reuse and avoiding future upstream fetch/parsing | Bucket, policies, object lifecycle, source-update invalidation, races and extra request/egress accounting |
| 5 | Base64 in JSON | 1 Edge invocation | Very small code change; 1.33x in this sample | Still text inflation and encode/decode work |

`Response` accepts binary body types and `FormData`
([MDN `Response()`](https://developer.mozilla.org/en-US/docs/Web/API/Response/Response));
`FormData` fields may contain `Blob`s
([MDN FormData guide](https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest_API/Using_FormData_Objects)).
The installed `@supabase/functions-js` client already maps
`application/pdf`/`application/octet-stream` to `Blob` and
`multipart/form-data` to `FormData`
([installed source](../node_modules/@supabase/functions-js/src/FunctionsClient.ts)).
However, MDN labels [`Response.formData()`](https://developer.mozilla.org/en-US/docs/Web/API/Response/formData)
as not Baseline across all widely used browser versions. Therefore multipart is
the lowest-complexity **candidate**, not something to ship without the project's
actual browser-matrix and deployed-function test. Do not manually set a multipart
`Content-Type`; the runtime must add its boundary.

### Storage, caching and billing

Storage becomes worthwhile only when repeat opens are common enough to avoid
re-downloading and re-parsing the same upstream files. Supabase documents an Edge
Function cache-first pattern and Storage CDN serving
([function/Storage integration](https://supabase.com/docs/guides/functions/storage-caching)).
Public objects give the highest cache-hit opportunity; private objects require an
authenticated request or time-limited signed URL
([serving Storage assets](https://supabase.com/docs/guides/storage/serving/downloads)).
That is an operational and access-policy decision, not merely a serialization fix.

Supabase bills Edge Functions by invocation regardless of response status, with
preflight `OPTIONS` excluded
([invocation accounting](https://supabase.com/docs/guides/platform/manage-your-usage/edge-function-invocations)).
A Storage download is not another Edge invocation, but Storage requests, stored
bytes and egress have their own usage dimensions. Supabase currently publishes a
256 MB memory limit, 2 seconds CPU per request and 150/400 second wall-clock limit;
its 20/5 MB figures are **function bundle limits**, not documented response-body
limits ([Edge Function limits](https://supabase.com/docs/guides/functions/limits)).

### Implemented result and remaining verification

Multipart is implemented while retaining the exact `answers` and `answerKey`
metadata. The largest golden PDF passed byte equality, metadata validation, the
installed Supabase Functions client, and a live local Edge invocation. A hosted
preview still needs the same hash/length and practice-only checks in the supported
browsers. If a supported browser or the hosted relay cannot parse the response,
use the length-prefixed envelope. Do not add Storage until request logs demonstrate
enough repeated papers to pay for the added state.

## CP-018 — hand-picked thresholds and derived scores

### What “hand-picked” means

[`model.ts`](../src/lib/stats/model.ts) clearly labels most tunable values as
`PICKED`: they are reasonable starting policies, but have not been estimated or
validated against this product's outcomes. That is different from structural or
published inputs:

| Category | Values in the current implementation |
|---|---|
| Published/mathematical | Wilson interval method and the 95% normal quantile `1.959964`; Cambridge session/paper grade thresholds; chance `1 / optionCount` |
| Structurally defined | A retention probability below `0.5` being past the modelled half-life; marks and option counts read from the paper |
| Literature-inspired but untrained here | Half-life regression form and `theta = [1, 1, -0.5]`; region-of-proximal-learning concept, but not its triangular kernel or chosen peak |
| Product/presentation choices | 80% grade range (`z = 1.281552`), minimum 40 grade questions, 20-question mastery half-life, fallback mastery `0.70`, six queue items |
| Uncalibrated decision rules | Queue weights `0.50/0.30/0.20`, queue minimum 8; gap/spread/trend/streak thresholds; confidence `0.70/0.40`; guess time `0.40` and exploration depth `1`; alert-rate and recency windows |

The Wilson method is a published small-sample binomial interval
([Wilson, 1927](https://doi.org/10.1080/01621459.1927.10502953)); Cambridge
publishes grade-threshold tables by exam series
([Cambridge International](https://www.cambridgeinternational.org/programmes-and-qualifications/exam-administration/results/grade-threshold-tables/));
and the half-life regression form is literature-backed, but its coefficients must
be learned from traces rather than inherited unchanged
([Settles & Meeder, 2016](https://aclanthology.org/P16-1174/)). A cited model form
does not validate the app's selected coefficients or product cut-offs.

There is a second, less visible set of hand-picked values outside `MODEL` in
[`enrichAnalytics.ts`](../src/lib/processing/enrichAnalytics.ts): confidence
weights `0.4/0.3/0.2/0.1`, difficulty weights
`0.4/0.25/0.2/0.1/0.05`, interest weights
`0.35/0.25/0.15/0.05/0.05/0.15`, the `0.5 + 0.25` diminishing transform, and
scales 5, 6 and 3. [`findOptimalSteepness.ts`](../src/lib/utils/findOptimalSteepness.ts)
also picks `2.5`. [`examSummary.ts`](../src/lib/types/examSummary.ts) duplicates
the guess thresholds instead of importing the central values, creating drift risk.

### Corrected correctness defect: three signals were inverted

`diminishing(0)` returns `1`; the first click returns `0.5`, subsequent clicks
fall toward `0.1`. That direction is sensible for using `Flag` as an inverse
confidence signal. It is then reused in places whose comments and positive weights
require the opposite direction:

- `markDifficultScore = diminishing(Star count)` means **not** starring a
  question maximizes its difficulty contribution; starring it lowers difficulty.
- `markSaveScore = diminishing(Save count)` means **not** saving a question
  maximizes its interest contribution; saving it lowers interest.
- `markReviewScore` is positively weighted into interest, so **not** flagging a
  question increases interest despite the comment describing “marked for review.”

This was more serious than uncertain calibration because it reversed explicit user
intent. The forward calculation now gives increasing and decreasing transforms
distinct roles, with a monotonicity test for Star, Save, and interest-from-Flag.
Existing version-1 rows retain their former values; do not compare or expose those
composites across the correction without a backfill or explicit version boundary.
The confidence comment also calls `Flag` a “right/wrong flag,” but the
implementation observes a user's review flag, not correctness.

### Better approach with little data

1. Correct directionality and centralize every inference constant, separating
   presentation caps/windows from statistical claims.
2. Label outputs as heuristic scores, expose their evidence components, and avoid
   presenting them as calibrated probabilities.
3. Replace brittle sample-count gates with explicit uncertainty: interval width or
   a posterior/lower-bound decision. The confidence level remains a policy choice,
   but its consequence is inspectable.
4. For the queue, prefer a lexicographic rule (e.g. evidence band, then decay, then
   marks) or sensitivity analysis over plausible weight ranges. Recommend an item
   only when it remains near the top across those ranges; this avoids false decimal
   precision without pretending there is training data.
5. Use per-user robust baselines/percentiles for rush and hesitation instead of
   global cuts. If acceptable UX-wise, ask for explicit low/medium/high confidence
   or difficulty occasionally to create a usable target.

### Data-calibrated stage

Define targets before training: confidence predicts held-out correctness using
pre-reveal behaviour; difficulty uses an explicit rating or population item
facility/time; interest predicts a **future** voluntary revisit rather than the
same Save event used as an input; the revision queue predicts later, unseen
same-topic improvement. Split chronologically and by user to prevent leakage, pool
sparsely observed subject/topic effects, then personalize only with enough evidence.

Evaluate probabilities with calibration plots and proper scores, then calibrate on
held-out data if necessary (modern calibration evidence:
[Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html)). Tune guess
thresholds for the chosen false-positive/false-negative cost. Recommendation impact
eventually needs an experiment because observational improvement is confounded by
which topics a motivated student chooses. The existing raw attempt events and
`metrics_versions` table provide the right foundation: version every semantic or
weight change and recompute rather than silently overwriting old meanings.

## CP-019 — Lottie warning and ECharts weight

### Lottie: cause and remedies

The build warning points to Lottie 5.13.0's expression engine, which compiles After
Effects expressions with `eval`
([upstream source](https://github.com/airbnb/lottie-web/blob/v5.13.0/player/js/utils/expressions/ExpressionManager.js#L438)).
The repository's loader is canvas-rendered, about 20 KiB of JSON, 76 frames and 11
shape layers, with no expression fields or external assets. Measured isolated
bundles were:

| Lottie build | Minified | Gzip | Contains `eval` warning site? |
|---|---:|---:|---|
| Default/full | 301.7 KiB | 77.5 KiB | Yes |
| `lottie_light_canvas` | 202.3 KiB | 56.0 KiB | No |

The upstream light-canvas module omits the expression plugin, while the full canvas
module adds it
([light canvas](https://github.com/airbnb/lottie-web/blob/v5.13.0/player/js/modules/canvas_light.js),
[full canvas](https://github.com/airbnb/lottie-web/blob/v5.13.0/player/js/modules/canvas.js)).

Recommended low-risk remedy: deep-import
`lottie-web/build/player/lottie_light_canvas`, update the Lottie `manualChunks`
entry to the same module, and visually sample the animation across its timeline.
Removing unused `vue3-lottie` also removes its nested Lottie 5.12.2 install. A CSS
or inline-SVG replacement is the lightest result and removes animation-library CPU,
but changes the visual implementation. Setting `runExpressions: false` or filtering
Rollup's `EVAL` warning only hides/disables runtime behaviour; the parsed `eval`
site and bundle bytes remain. If suppression is consciously chosen, scope it to the
specific package and warning code using Rollup's documented `onwarn` hook
([Rollup warnings](https://rollupjs.org/configuration-options/#onwarn)).

### ECharts: what is already good

[`echarts.ts`](../src/lib/charts/echarts.ts) already follows ECharts' tree-shakeable
`echarts/core` plus explicit charts/components/renderer pattern
([official import guide](https://echarts.apache.org/handbook/en/basics/import/)).
There is no whole-library `import 'echarts'` in application source. Measured current
registration is **660.7 KiB minified / 225.6 KiB gzip**. Removing
`DatasetComponent`, `TitleComponent`, `LabelLayout`, and `UniversalTransition`
measured **629.5 / 214.0 KiB**, only about 5%. A safer first pass is to remove
`DatasetComponent`, `TitleComponent`, and `UniversalTransition`, then visually
check labels before deciding whether `LabelLayout` is redundant.

The bigger issue is eager work: Stats renders 13 `EChart` instances, all sections
start expanded, and collapse uses `v-show`, which does not unmount or defer them.
The header subject pie also makes ECharts an above-the-fold dependency.

### Optimizations, ranked

1. **Prune unused registrations** and test all chart types. This is easy but a small
   transfer win.
2. **Fix load timing:** split the theme/type helpers from the runtime, dynamically
   import the registered ECharts runtime in `EChart.vue`, and mount below-fold
   charts near the viewport with `IntersectionObserver` (or `v-if` for genuinely
   collapsed sections). Replace the simple header pie with accessible CSS/SVG if
   ECharts should be absent from initial Stats load. Vite supports splitting dynamic
   imports and preloading their common dependencies
   ([Vite async chunk loading](https://v6.vite.dev/guide/features#async-chunk-loading-optimization)).
3. **Feature-level dynamic registration** only if measurements justify it: a base
   module plus pie, line/bar, scatter/mark-line and heatmap/visual-map loaders.
   `echarts.use()` is additive on the shared singleton, so ordering and every lazy
   route need integration tests. A single eager chart defeats most of this benefit.
4. **Do not switch globally to SVG for size.** Local measurement showed no bundle
   win, and the page includes a heatmap. ECharts documents Canvas as preferable for
   larger data and SVG as useful for lower memory and many small/mobile instances
   ([renderer comparison](https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/)).

Raising Vite's `chunkSizeWarningLimit` only suppresses a diagnostic. Vite documents
the default as 500 kB and compares uncompressed size because it relates to execution
time ([Vite build options](https://v6.vite.dev/config/build-options#build-chunksizewarninglimit)).
Likewise, dividing still-eager ECharts code into arbitrary manual chunks does not
reduce transfer or parsing; Rollup warns that manual chunks can also change when
side effects run
([Rollup `manualChunks`](https://rollupjs.org/configuration-options/#output-manualchunks)).

## Acceptance measurements for any implementation

- CP-016: response bytes, Edge duration/memory, browser decode time, PDF hash, full
  answer-row equality, cold/repeat request count, and practice-only failure mode.
- CP-018: monotonicity unit tests, held-out calibration/error metrics, sample count,
  and version identifier displayed or logged with every derived score.
- CP-019: production chunk gzip/raw sizes, Stats route LCP/INP and time-to-first
  chart, chart instance count before scrolling, animation frame screenshots, and a
  build log with no Lottie `EVAL` warning.
