<!-- ==========================================================================
     It is documentation only; it contains no application code.
     It records how SmartSolver-Merged was assembled from the three prongs
     under SmartSolver/, and what work remains.
     ========================================================================== -->

# SmartSolver-Merged

Assembled from the three prongs that previously sat under `SmartSolver/`.
**No application source file was rewritten.** Every `.vue`, `.ts`, `.scss` and `.css`
file here is byte-identical to one of the originals. The only edited file is
`package.json` (§4), because the merged app could not install without it.

---

## 1. What was found

| Prong | Newest source file | src LOC | Verdict |
|---|---|---|---|
| `cards/` | 2025-05-02 | 1,468 | **Ancestor.** Its `components/` (Card, CardGrid, Tag) evolved into dashboard's `components_browser/`. |
| `smartsolver/` | 2025-12-24 | 2,308 | **Ancestor**, but holds pieces dashboard lost. |
| `dashboard/DraggableDashboard/vite-project/` | **2025-12-29** | **6,289** | **Current main line.** Chosen as the base. |

`dashboard/` is the successor by every measure: newest mtimes, ~2.7× the code, and
it is the only prong with a design system (`src/styles/*.scss`), self-hosted fonts
(Inter, Kode Mono, Lexend, Poppins), an icon set, and all four page groups
(dashboard, browser, stats, navigator).

**Correction to an earlier assessment in `SMARTSOLVER_CAMBRIDGE_MERGE_PLAN.md`:** that
document called `dashboard/` an empty shell holding "only configs". That was wrong —
its `src/` was simply missed. Treat §1.2 and §3 of that plan as superseded by this file.

### The merge was genuinely necessary

`dashboard/` **does not build on its own.** Two independent breakages:

1. **Three dangling imports.** `dashboard/src/lib/` still imports from `../buttons`
   and `../render/renderTracks`, but those files exist only in `smartsolver/`:
   - `src/lib/processing/enrichAnalytics.ts:1` → `../buttons`
   - `src/lib/utils/utilsTypes.ts:1` → `../buttons`
   - `src/lib/pdf/createPDFObservers.ts:2,7` → `../buttons`, `../render/renderTracks`
2. **Three runtime deps missing from its `package.json`**: `@supabase/supabase-js`,
   `pdfjs-dist`, `lucide-vue-next` — all three are imported by its own source.

Both are fixed here.

---

## 2. Files brought forward from `smartsolver/` — all byte-identical

Verified with `cmp`; none were modified.

```
src/lib/buttons/buttonTypes.ts          resolves ../buttons for utilsTypes + enrichAnalytics
src/lib/buttons/createTrackButtons.ts
src/lib/buttons/createTracks.ts
src/lib/buttons/handleButtonClick.ts    the Copy/Flag/Star/Save → addEventLog behaviour
src/lib/buttons/index.ts
src/lib/render/renderTracks.ts          resolves ../render/renderTracks for createPDFObservers
src/lib/render/renderTrackButton.ts
schema.sql                              dashboard prong had no DB schema at all
```

**Deliberately not brought forward.** These exist in `smartsolver/src/lib/` but
dashboard has no reference to them — it replaced the mechanisms, so re-adding them
would be re-introducing dead code:

- `pdf/graphicsToBoundingBoxes.ts` — dashboard's `getOptions.ts` (260 LOC vs 102) was
  rewritten and no longer needs it
- `utils/observePDFScaleChanges.ts`, `utils/getCurrentScale.ts` — dashboard's
  `MCQNav.vue` runs its own `MutationObserver` for scale

`call_fetch_pdf.sh` was **not copied**: it contains a real email address and a
plaintext password. See §6.13.

---

## 3. What came from `cards/`

Split by whether dashboard supersedes it.

**`corpus/` — kept live** (not superseded; dashboard has no equivalent):
```
corpus/syllabus_papers/     130 files, 34 MB — CAIE syllabus PDFs + extracted .txt
corpus/urls.txt
corpus/variant_codes.txt
corpus/gv.py
```

**`legacy/cards/` — preserved, not wired into the build**:
```
legacy/cards/src/components/       Card.vue, CardGrid.vue, Tag.vue
                                   → superseded by src/components_browser/*
                                     (dashboard's Card.vue is a strict superset:
                                      274 LOC → 349, adds computed + CSSProperties)
legacy/cards/src/stats-components/ Rankings.vue, Stats.vue, Subject-Card.vue,
                                   Subject-Page.vue, Wave-Generator.vue
                                   → a different, older design (FontAwesome trophies,
                                     gold pedestals). Stats.vue imports
                                     ./Pedestal-Block.vue, WHICH DOES NOT EXIST,
                                     so this tree cannot compile as-is.
legacy/cards/public/               gold-pedestal.obj, Gold.mtl, model*.png,
                                   location pins, circle-scatter-haikei.svg
```

Nothing under `legacy/` is imported by `src/`, so it cannot break the build. Promote
anything you still want by moving it into `src/` and fixing its imports.

---

## 4. The only edited file: `package.json`

Every change, exactly (JSON cannot carry comments, so they are itemised here):

| Change | From | To | Why |
|---|---|---|---|
| `name` | `"vite-project"` | `"smartsolver-merged"` | the base prong carried the scaffold's default name |
| **added** dep | — | `"@supabase/supabase-js": "^2.84.0"` | imported by `src/stores/useAuth.ts`, was undeclared |
| **added** dep | — | `"pdfjs-dist": "^5.4.394"` | imported by `src/lib/pdf/*`, was undeclared |
| **added** dep | — | `"lucide-vue-next": "^0.555.0"` | imported by `src/components_navigator/ActiveQuestionButtons.vue`, was undeclared |
| **removed** dep | `"vite-project": "file:"` | — | a self-referential dependency on the old package name; an npm-install hazard and plainly a scaffold artifact |

Versions for the three added deps were taken from `smartsolver/package.json` (the two
it shared) and from the stray `SmartSolver/package.json` (`lucide-vue-next`), so
nothing was invented.

`package-lock.json` was **deleted and regenerated** by `npm install`. The old one
locked a dependency set that provably did not match the source (missing all three
deps above) and contained the self-referential entry.

Nothing else was touched: `vite.config.ts`, all three `tsconfig*.json`, `index.html`,
`.gitignore`, `src/**`, `supabase/**` and `public/**` are exactly as they were in the
dashboard prong.

---

## 5. Verification actually run

| Check | Result |
|---|---|
| `npm install` | ✅ 119 packages, 35 s. Warnings only (`lucide-vue-next` deprecated → `@lucide/vue`; a transitive Vue 2 EOL notice). |
| Unresolved local imports (`@/…` and relative, `?raw` stripped) | ✅ **0** — was 3 before the merge |
| `npx vite build` | ✅ 1,918 modules, 22.4 s → `dist/` |
| `npx vue-tsc -b` | ⚠️ **22 errors** — down from **25** in the unmerged dashboard prong (measured, not estimated) |

The type-error baseline was measured by type-checking an untouched copy of the
dashboard prong against this same `node_modules`. The merge removed the 3
module-not-found errors and introduced none; all 22 remaining are pre-existing
dashboard issues (§6.8).

**`npm run build` still fails**, because that script is `vue-tsc -b && vite build` and
`vue-tsc` is non-zero. Use `npx vite build` until §6.8 is cleared. The bundle itself
is fine — that was verified independently.

---

## 6. Outstanding work

Ordered by what blocks the most.

### 6.1 The stats page renders no real data — **biggest gap**
`src/components_stats/` is visually complete (`StatsPage.vue` 258 LOC + 6
sub-components, sections for progress / engagement / focus) but **contains not one
database call**. Specifically:
- `StatsPage.vue:10–17` — the three `Multiselect` filters are hardcoded to
  `['Wade Cooper','Arlene Mccoy','Devon Webb','Tom Cook']`, `['Apple','Banana','Cherry']`,
  `['Red','Green','Blue']`. They should be years / seasons / variants.
- `StatsPage.vue:33` — the page subtitle is Lorem ipsum.
- `CardStrip.vue:4` — `const testStats = Array.from({length: 30}, …)` is generated placeholder data.
- `.pie-container` (`StatsPage.vue:56`) is an empty div.

Needs a query layer over `exam_attempts` + `question_attempts` and the filters bound to it.

### 6.2 Correctness is never persisted — blocks any accuracy metric
`getQuestionsAnalytics` computes `qCorrect` per question, but `pushToAttemptsTable`
never sends it and `schema.sql` has no column for it. **Accuracy, scores and
mark-based progress cannot be shown from the database as it stands.** Needs a
`question_attempts.is_correct boolean` column plus one line in the write payload.

### 6.3 `time_spent_ms` actually stores seconds
`startFocusAreaTimer.ts` accumulates `deltaSeconds` (`active.time += deltaSeconds`);
`pushToAttemptsTable.ts` writes that straight into the `time_spent_ms` column. Meanwhile
`hesitation_time_ms` (from `performance.now()` deltas) and `exam_attempts.total_time_ms`
are genuine milliseconds. **Two time columns in the same schema are in different units.**
Any stats work must fix this first or it will silently render 1000× wrong values.

### 6.4 The question flag buttons are inert
`ActiveQuestionButtons.vue` renders Copy / Flag / Star / Save as bare `<button>`s with
**no click handlers and no `addEventLog` call**. Consequences in `enrichAnalytics.ts`:
`markedForReview`, `markedAsDifficult` and `markedForSave` are always 0, so
`markReviewScore` / `markDifficultScore` / `markSaveScore` are pinned at 1 — and those
carry 0.4 of the confidence score, 0.4 of difficulty and 0.35 of interest. **Three of
the headline metrics are substantially constant right now.**
The behaviour exists in `src/lib/buttons/handleButtonClick.ts` (brought forward in §2);
it just needs wiring to the new Vue buttons.

### 6.5 `createPDFObservers.ts` is dead and signature-mismatched
No module imports it. Its `renderTracks(tracks, pages, totalScale, eventLogs)` call at
line 29 does not match smartsolver's `renderTracks(buttonTracks, pageIndexes, totalScale, eventLogs)`
signature — hence the surviving `number[]` vs `Ref<number>` error. Either wire it up (it is
how button tracks used to reach the page) or delete it. Do not leave it half-alive.

### 6.6 No RLS policies
`schema.sql` creates `attempts`, `exam_attempts` and `question_attempts` but defines
**no row-level-security policies**. Under Supabase's default-deny this means the client
cannot read or write them on a real project; it works locally only because the dev stack
is permissive. Every table needs a policy keyed on `user_id`.

### 6.7 Supabase endpoint is hardcoded to localhost
`src/stores/useAuth.ts` builds its client against `http://127.0.0.1:54321`. Move the URL
and publishable key to `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`.

### 6.8 22 type errors block `npm run build`
| Category | Count | Note |
|---|---|---|
| Unused imports / locals (`TS6133`) | 10 | `MetaBar`, `onMounted`, `props`, `options1`, `selected1`, `color`, `watch`, `startExam`, `endExam`, `ref`, `Circle` |
| Missing `.vue` module shim (`TS7016`) | 5 | `src/vite-env.d.ts` is only `/// <reference types="vite/client" />`; it needs the `declare module '*.vue'` block |
| `Card` prop `color` mismatch (`TS2719`/`TS2339`) | 2 | two unrelated `Card` types; `color` required by one, absent on the other |
| `addEventLog` union widening (`TS2322`) | 2 | signature takes `string`, `EventLogs` wants the literal unions |
| `identifyQuestionNumbers` predicate (`TS2769`) | 1 | mapped object is missing 5 `indexed_textbox` fields |
| `createPDFObservers` arg order (`TS2345`) | 1 | see §6.5 |

The 5 shim errors are one four-line fix in `vite-env.d.ts` and the 10 unused imports are
deletions — that is 15 of 22 cleared cheaply.

### 6.9 `Sidebar` imported but never rendered in `App.vue`
`src/App.vue` imports `Sidebar` and its template is only `<RouterView>`. Each page
(`StatsPage`, `BrowserPage`, …) renders its own `<Sidebar>`, so the import is dead —
harmless at runtime, but it is one of the `TS6133`s.

### 6.10 `fetch-pdf` sends no CORS headers
`supabase/functions/fetch-pdf/index.ts` has no `OPTIONS` branch and sets no
`Access-Control-Allow-*`. Its caller sends `Authorization` + `Content-Type: application/json`,
which forces a preflight. Works only because everything is on localhost today; it will
fail the moment the function is deployed to a `*.supabase.co` origin.

### 6.11 Single 1.4 MB JS chunk
`dist/assets/index-*.js` is 1,407 kB (385 kB gzipped), over Vite's warning threshold.
Route-level `import()` or `manualChunks` for `pdfjs-dist` / `@supabase/supabase-js` /
`lottie-web` would cut first paint substantially. `paper.png` is a further 1.75 MB.

### 6.12 Four declared-but-unimported dependencies
`@vueform/toggle`, `cytoscape`, `vue-slider-component`, `vue3-lottie` are in
`package.json` with no importer. Kept, because dropping them is a judgement call about
planned work, not a merge decision. `lucide` (the vanilla package) is used only by the
`src/lib/buttons/` code brought forward in §2 — keep it; `lucide-vue-next` is the Vue
binding used by the newer components, so both are legitimately present.

### 6.13 Rotate the leaked test credentials
`smartsolver/call_fetch_pdf.sh` contains a real email and a plaintext password. It was
**not** copied here, but it still exists in the original prong and predates this merge.
Rotate that account's password and keep the file out of version control (or make it read
`$SS_EMAIL` / `$SS_PASSWORD`).

---

## 7. Running it

```bash
cd SmartSolver-Merged
npm install
npx vite build          # works today
npm run dev             # Vite dev server
# npm run build         # blocked by §6.8 until vue-tsc is clean
```

Routes (`src/router/router.ts`, unchanged from the dashboard prong):

| Path | Component |
|---|---|
| `/` | `components_dashboard/DashboardPage.vue` |
| `/browser` | `components_browser/BrowserPage.vue` |
| `/stats` | `components_stats/StatsPage.vue` |
| `/solver/:schema` | `components_navigator/MCQNav.vue` |
| `/login` | `components_auth/Login.vue` |

The Supabase stack still runs separately (`supabase start`, then
`supabase functions serve fetch-pdf`) against `supabase/config.toml`.

---

## 8. Originals

`smartsolver/`, `cards/` and `dashboard/` were **not modified or deleted** — this is a
copy. Delete them once you have confirmed the merged app behaves, and note that
`smartsolver/` is the only prong that still holds `call_fetch_pdf.sh` (§6.13).
