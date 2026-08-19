# SmartSolver × Cambridge Pseudocode — Single-App Merge Plan

**Status:** analysis + plan only. No code has been changed.
**Date:** 2026-08-17
**Scope:** merge the SmartSolver MCQ app (`SmartSolver/smartsolver/`) into the Cambridge
pseudocode web app (`src/website/frontend/`) so one Vue SPA serves two products:
**MCQ Solver** and **Pseudocode Solver**.
**Explicitly out of scope (owner will do manually):** the Supabase ↔ Firebase database
question. This plan keeps both data layers side by side and running, and isolates every
place a future consolidation will have to touch (§13).

---

## 0. Verdict

**Yes — this merge is not just possible, it is unusually cheap.** Both apps are
Vue 3 + Vite + `vue-router` SPAs, both already use the `@` → `src` alias, and there is
**zero filename or module-path collision** between the two source trees. The great majority
of SmartSolver's code (its entire `src/lib/**` — 62 files, ~1,700 LOC of PDF parsing,
highlighting, focus-area timing, event logging and analytics) moves **byte-for-byte unchanged**.

The work is concentrated in six places:

| # | Area | Difficulty | Why |
|---|------|-----------|-----|
| 1 | Global CSS leakage from SmartSolver | **High** | `MCQNav.css` ships a `* { … }` reset that will overwrite the Cambridge design system app-wide (§6.1) |
| 2 | Router unification (hash vs history) | **Medium** | Cambridge uses `createWebHashHistory`; SmartSolver assumes `createWebHistory` (§7) |
| 3 | `X-Frame-Options: DENY` kills the PDF iframe | **Medium** | Latent production-only breakage, present in *both* `vercel.json` and `firebase.json` (§6.3) |
| 4 | Two auth systems on one route guard | **Medium** | Firebase guard would lock MCQ routes out (§8) |
| 5 | Toolchain: TS, Pinia, SCSS, new deps | **Low** | Additive to `package.json` + one `tsconfig` (§9) |
| 6 | 16 MB of vendored pdf.js assets | **Low** | Must land in `public/`, must be excluded from the Vercel Function bundle (§10) |

Nothing here is architectural. There is no rewrite. Estimated effort: **one focused day**
for a working merged app, plus a second pass for polish and the deferred DB work.

---

## 1. Inventory — what actually exists

### 1.1 Cambridge Pseudocode app (the host)

Repo root is a **Python pipeline + Vue frontend** monorepo. Only the web parts matter here.

```
package.json                       root owns ALL JS deps (Vercel Root Directory = repo root)
vercel.json                        framework: vite, buildCommand: npm run build,
                                   outputDirectory: src/website/static, api/grade.py Function
firebase.json                      hosting site "smartsolver" (!), public: src/website/static,
                                   RTDB rules, emulators (auth 9099, database 9000)
database.rules.json                RTDB security rules
api/grade.py           (208 LOC)   Vercel Python Function — /api/grade
api/_quota.py          (121 LOC)   per-uid rate limiting via RTDB REST
src/website/
  frontend/
    index.html                     pre-paint theme bootstrap, Fontshare "General Sans"
    vite.config.js                 root=frontend, base='./', outDir=../static,
                                   alias @ -> ./src, dev-only /api/grade middleware plugin
    jsconfig.json                  paths: @/* -> ./src/*
    public/
      resources/                   45 MB — question PNGs + records JSON + layouts JSON
      wasm/pseudocode_parser.wasm  260 KB — Rust compiler compiled to wasm
    src/
      main.js              (14)    imports main.css, initializeTheme(), router, mount
      App.vue              (63)    topbar chrome, honours route.meta.chrome === false
      router/index.js      (63)    createWebHashHistory, 6 routes, auth guard on non-public
      assets/main.css    (1428)    the entire design system (light/dark tokens, all components)
      components/                  BlankFieldsPanel, CodeEditor, EditorPanel, FilterPanel,
                                   ProblemExplorer, QuestionPanel, ResultsPanel,
                                   SelectableQuestionImage, SelectableTextOverlay,
                                   TagChips, TerminalPanel, ThemeToggle
      views/                       LandingView(434), LearnView(381), IdeView(284),
                                   LoginView(247), ProblemsView(122)
      services/                    firebase.js, auth.js, theme.js, records.js, grading.js,
                                   userProgress.js, staticParser.js, wasmParser.js,
                                   tags.js, pseudocodeLanguage.js, imageAvailability.js
  static/                          Vite build output (gitignored)
  server_resources/grading_question_records.json.gz
tests/frontend_*.test.mjs          node --test, imports services/records.js directly
```

Installed & pinned: **vue 3.5.40, vue-router 5.2.0, vite 8.1.5, @vitejs/plugin-vue 6.0.8**,
`firebase ^12.16.0`, CodeMirror 6, `@fontsource/ibm-plex-mono`, `esbuild` (for the wasm build script).

**Language: plain JavaScript.** No TypeScript, no Pinia, no SCSS anywhere in the host app.

### 1.2 SmartSolver app (the guest)

`SmartSolver/` is **untracked** (`git status` shows `?? SmartSolver/`) and contains three
unrelated sub-projects. **Only `SmartSolver/smartsolver/` is in scope.**

```
SmartSolver/
  package.json                 stray root manifest, no name/scripts — ignore
  smartsolver/                 <-- THE MCQ APP (in scope)
  cards/                       separate Vue experiment: subject cards, syllabus PDFs,
                               vite 6, no router — OUT OF SCOPE
  dashboard/DraggableDashboard/vite-project/
                               separate Vue experiment: cytoscape, lottie, vue-slider,
                               source dir is EMPTY (only configs) — OUT OF SCOPE
  supabase/                    stray CLI state (.temp, .branches) — ignore
```

`SmartSolver/smartsolver/`:

```
index.html                     stock Vite template ("my-vue-app", /vite.svg favicon)
package.json                   name "my-vue-app", build = "vue-tsc -b && vite build"
vite.config.ts                 plugins:[vue()], alias @ -> ./src   (no base, no outDir)
tsconfig.json / .app.json      extends @vue/tsconfig/tsconfig.dom.json, strict,
                               noUnusedLocals, noUnusedParameters, erasableSyntaxOnly
schema.sql                     attempts / exam_attempts / question_attempts
call_fetch_pdf.sh              ⚠ CONTAINS A REAL EMAIL + PLAINTEXT PASSWORD
public/web/     (7.1 MB)       vendored pdf.js viewer — viewer.html/js/css, pdf.js v3.2.146
public/build/   (9.2 MB)       vendored pdf.js core + worker + sandbox (+ .map files)
supabase/config.toml           local stack: API 54321, DB 54322
supabase/functions/fetch-pdf/  Deno edge function: downloads QP+MS from papacambridge,
                               parses the MS answer table, returns { qp: number[], answers }
src/
  main.ts              (12)    createApp, use(router), use(createPinia()), mount
  router.ts            (20)    createWebHistory; /login, /dashboard, /mcq/:schema (props)
  App.vue              (21)    sidebar shell, imports ./style.css, calls useAuthStore().init()
  style.css            (28)    .app-container/.sidebar/.main-content/.nav-link
  stores/useAuth.ts    (58)    Pinia store; createClient(localhost:54321, publishable key);
                               init/login(email|oauth)/logout; router.push("/dashboard")
  components/
    MCQNavigator/MCQNav.vue    (233)  THE core screen — see §1.3
    MCQNavigator/MCQNav.css     (78)  ⚠ global `*` reset + Inter @import
    MCQNavigator/MCQComponents/endScreen.vue   EMPTY STUB
    Dashboard/Dashboard.vue     (21)  two links into /mcq/:schema
    Dashboard/Dashboard.css     (18)
    Login/Login.vue             (33)  Google/Twitter/Azure OAuth + email/password
    Stats/Stats.vue + .css            EMPTY STUBS
    Landing Page/Landing.vue + .css   EMPTY (0 bytes) — folder name contains a SPACE
  lib/                         62 files — the real engine, all framework-light:
    pdf/          extractText, identifyQuestionNumbers, segmentQuestions, getOptions,
                  detectOptionFont, extractGraphics, graphicsToBoundingBoxes,
                  getGraphFont, getGraphScore, createPDFObservers, pdfTypes
    highlights/   createHighlights, selectOption (correct/eliminated/neutral state machine)
    focusAreas/   createFocusAreas, eventListenersInit, startFocusAreaTimer, getActiveFocusArea
    buttons/      createTracks, createTrackButtons, handleButtonClick (Copy/Flag/Star/Save)
    render/       renderHighlights, renderFocusAreas, renderTracks, renderTrackButton
    processing/   getQuestionAnalytics, enrichAnalytics (256 LOC of the metrics model),
                  partitionLogsByQuestion, processingTypes
    supabase/     pushToExamTable, pushToAttemptsTable, lettersToMask, letterToIndex
    utils/        addEventLog, computeGlobalIndex, throttle, clamp, sigmoid, meanStd,
                  normalizeWeights, findOptimalSteepness, timeToConfidence,
                  observePDFScaleChanges, getCurrentScale, keydownListeners, utilsTypes
  assets/soluer-loader.json    UNUSED (no importer)
```

Declared deps: `@supabase/supabase-js ^2.84.0`, `lucide ^0.554.0`, `pdfjs-dist ^5.4.394`,
`phosphor-icons` (**unused**), `pinia ^3.0.4`, `supabase` (the **CLI**, wrongly a runtime dep),
`vue ^3.5.25`, `vue-router ^4.6.3`. Dev: `sass-embedded`, `typescript ~5.9.3`, `vue-tsc`,
`@types/node`, `@vue/tsconfig`.

**`SmartSolver/smartsolver/node_modules` does not exist** — the app has not been installed
in this checkout, so nothing has ever been built here. Assume it is untested locally.

### 1.3 What `MCQNav.vue` actually does (must be preserved exactly)

1. Reads `props.schema` (e.g. `0625_s25_22`) from the route.
2. Requires a Supabase session; otherwise `router.push("/login")`.
3. `POST http://127.0.0.1:54321/functions/v1/fetch-pdf` with the JWT → `{ qp: number[], answers: TableRow[] }`.
4. Builds a `Blob` → `URL.createObjectURL` → sets `iframe.src = '/web/viewer.html?file=<blob url>'`.
5. On iframe `load`: registers `keydown` handlers on **both** windows (C = correct mode, E = eliminate mode),
   injects `.highlight` / `.focus-area` / `.focus-area-timer` CSS **into the iframe document**,
   awaits `PDFViewerApplication.initializedPromise`.
6. On the viewer's `pagesloaded` event: re-parses the same bytes with the **iframe's** `pdfjsLib`,
   then runs `extractText → identifyQuestionNumbers → segmentQuestions → getOptions`
   → `createHighlights`, `createFocusAreas`, `createTracks`.
7. `observePDFScaleChanges` (MutationObserver on `--scale-factor`), `eventListenersInit`
   (click/mousemove/mouseleave → `eventLogs`), `startFocusAreaTimer` (1 s tick on the active area),
   `createPDFObservers` (IntersectionObserver + MutationObserver on `.textLayer` → renders
   highlights/focus areas/button tracks per visible page).
8. `endExam()`: `getQuestionsAnalytics` → `enrichAnalytics` → `pushToExamTable` → `pushToAttemptsTable`.

Everything above is DOM/iframe work that is completely independent of the host app's
component tree. **That is why this merge is cheap.**

---

## 2. Architecture comparison

| Concern | Cambridge (host) | SmartSolver (guest) | Merge decision |
|---|---|---|---|
| Framework | Vue 3.5 SFC, `<script setup>` | same | — |
| Language | JavaScript | TypeScript (strict) | keep both; Vite transpiles TS natively (§9.3) |
| Router | `vue-router` **5.2.0**, `createWebHashHistory` | `vue-router` **4.6.3**, `createWebHistory` | one router, v5, **hash** history (§7) |
| State | module-scope `ref`s in `services/*` | **Pinia** store | add Pinia; both coexist (§9.2) |
| Styling | one global `assets/main.css` + `<style scoped>` | global CSS imported from `<script setup>` | isolate guest CSS (§6.1) |
| Design tokens | `--bg/--ink/--accent/--panel` + light/dark | hardcoded `#007BFF`, `#3498db`, `white` | preserve as-is now, retheme later (§6.4) |
| Fonts | General Sans (Fontshare) + IBM Plex Mono | Inter (`@import` from Google Fonts) | keep Inter scoped to MCQ (§6.1) |
| Auth | Firebase Auth (email + Google) | Supabase Auth (email + Google/Twitter/Azure) | dual provider, guard made provider-aware (§8) |
| DB | Firebase RTDB (`users/$uid/…`) | Supabase Postgres (3 tables) | **untouched — owner's task** (§13) |
| Server | Vercel Python Function `/api/grade` | Supabase Deno Edge Function `fetch-pdf` | both stay; different origins (§10.3) |
| Build out | `src/website/static` | none configured | single build → `src/website/static` |
| Type check | none | `vue-tsc -b` in `build` | **not** wired into the root build (§9.3) |

---

## 3. Target structure

Guiding rule: **the `@` alias makes almost every SmartSolver import portable.** SmartSolver
imports `@/lib/…`, `@/stores/useAuth`, `@/router`, and relative `./X.css`. If the guest tree is
dropped into the host's `src/` preserving those three top-level names, **every one of those
imports keeps resolving with no edit**, including `import router from '@/router'` — which
resolves to the host's `src/router/index.js` and exports a compatible default.

```
src/website/frontend/
  index.html                       ← MODIFIED (title + no new global CSS; §9.4)
  vite.config.js                   ← MODIFIED (no functional change required; §9.5)
  tsconfig.json                    ← NEW  (replaces jsconfig.json; §9.3)
  public/
    resources/  wasm/              (unchanged)
    web/                           ← NEW, verbatim from SmartSolver/smartsolver/public/web/
    build/                         ← NEW, verbatim from SmartSolver/smartsolver/public/build/
  src/
    main.js                        ← MODIFIED (Pinia + auth init; §9.2)
    App.vue                        ← MODIFIED (product switcher in topbar; §5.2)
    router/index.js                ← MODIFIED (MCQ routes + provider-aware guard; §7, §8)
    assets/
      main.css                     (unchanged)
      soluer-loader.json            ← NEW, verbatim (unused, kept for parity)
    components/                    (host components unchanged)
      mcq/                         ← NEW subtree, from SmartSolver src/components/
        McqShell.vue               ← NEW (replaces SmartSolver App.vue sidebar; §5.2)
        MCQNavigator/
          MCQNav.vue               ← 5 labelled edits (§4.1)
          MCQNav.css               ← rewritten scoping only (§6.1)
          MCQComponents/endScreen.vue   verbatim (empty stub)
        Dashboard/Dashboard.vue    verbatim ✅
        Dashboard/Dashboard.css    ← 1 labelled edit (§6.2)
        Login/Login.vue            ← 1 labelled edit (§4.3)
        Stats/Stats.vue            verbatim (empty stub)
    lib/                           ← NEW, VERBATIM — all 62 files, zero edits ✅
    stores/
      useAuth.ts                   ← 3 labelled edits (§4.2)
    services/                      (host services unchanged)
    styles/
      mcq-shell.css                ← NEW, from SmartSolver src/style.css (§6.2)
    views/                         (host views unchanged)
  supabase/                        ← NEW (moved out of the app tree)
    config.toml, schema.sql, functions/fetch-pdf/
```

**Deliberately NOT copied:**

| Guest file | Reason |
|---|---|
| `src/main.ts` | superseded by host `main.js`; its two behaviours are ported (§9.2) |
| `src/router.ts` | superseded by host `router/index.js`; routes ported (§7) |
| `src/App.vue` | superseded by host `App.vue`; sidebar → `McqShell.vue` (§5.2) |
| `index.html`, `vite.config.ts`, `tsconfig*.json`, `package*.json` | host equivalents win |
| `components/Landing Page/` | 0-byte files; folder name contains a space |
| `call_fetch_pdf.sh` | **contains a live email + plaintext password — must not be committed.** Keep out of the repo, or rewrite to read `$SS_EMAIL`/`$SS_PASSWORD` from the environment before it lands. |
| `SmartSolver/cards/`, `SmartSolver/dashboard/` | unrelated projects, out of scope |
| `.vscode/`, `.stfolder/`, `.stignore`, `supabase/.temp`, `supabase/.branches` | local tool state |

---

## 4. Every change to SmartSolver code, exactly

### 4.0 The AI comment convention

Every line of SmartSolver-derived code that differs from the original gets a marker.
Use the comment syntax native to the file:

```js
// AI-MERGE: <what changed> — <why>. Original: <the original expression>
```
```css
/* AI-MERGE: <what changed> — <why>. Original: <the original selector/decl> */
```
```html
<!-- AI-MERGE: <what changed> — <why>. -->
```

Files created during the merge that have no SmartSolver original are headed with:

```js
// AI-MERGE-NEW: <file> — created during the SmartSolver→Cambridge merge; replaces <origin>.
```

Any file copied with **zero** changes gets **no** marker — absence of a marker is the
signal that the file is byte-identical to the SmartSolver original. Verify with:

```bash
diff -r SmartSolver/smartsolver/src/lib src/website/frontend/src/lib   # must be empty
```

### 4.1 `components/mcq/MCQNavigator/MCQNav.vue` — 5 edits

| Line (orig) | Original | Change | Why |
|---|---|---|---|
| 2 | `import "./MCQNav.css";` | keep the import, but the CSS file itself is re-scoped (§6.1) | a `<script setup>` CSS import is **global and permanent** for the session |
| 22 | `createClient("http://127.0.0.1:54321", "sb_publishable_…")` | `createClient(SUPABASE_URL, SUPABASE_ANON_KEY)` imported from a new `@/services/supabase.js` | hardcoded localhost cannot ship; also removes the second, duplicate client |
| 56 | `fetch('http://127.0.0.1:54321/functions/v1/fetch-pdf', …)` | `fetch(`${SUPABASE_URL}/functions/v1/fetch-pdf`, …)` | same |
| 89 | `iframe.src = '/web/viewer.html?file=' + …` | `iframe.src = `${import.meta.env.BASE_URL}web/viewer.html?file=` + …` | host Vite uses `base: './'`; a leading `/` works today but breaks under any sub-path deploy |
| 225–232 | `<style lang="scss">` with a bare `iframe { … }` selector | add `scoped`; keep the rules unchanged | a global `iframe {height:100%}` would hit any future iframe in the host app. `#loading-status` is an id and survives scoping (Vue rewrites it to `#loading-status[data-v-…]`, which still matches the element in this component's own template) |

Example of the exact form for line 22:

```ts
// AI-MERGE: Supabase client moved to @/services/supabase so URL + key come from Vite env
// instead of a hardcoded local stack. Original:
//   const supabase = createClient("http://127.0.0.1:54321", "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH");
import { supabase } from "@/services/supabase";
```

**Everything else in this file — all 233 lines of lifecycle, iframe wiring, event
registration, `endExam()` — stays exactly as written.** Including the `console.log`s.

### 4.2 `stores/useAuth.ts` — 3 edits

| Line | Original | Change | Why |
|---|---|---|---|
| 8 | `createClient("http://127.0.0.1:54321", "sb_publishable_…")` | import the shared client from `@/services/supabase` | same as above; also stops two independent `GoTrueClient` instances racing on the same storage key (a real Supabase warning) |
| 30 | `redirectTo: `${location.origin}/${redirect}`` | `redirectTo: `${location.origin}${import.meta.env.BASE_URL}#/${redirect}`` | the merged router is **hash**-based; `origin + "/dashboard"` would 404 (§7.2) |
| 41 | `router.push("/dashboard")` | `router.push("/mcq")` | the MCQ dashboard's path in the merged router (§7.1) |

`import router from '@/router'` on line 6 **needs no change** — it now resolves to the host
router, which exports a compatible default.

### 4.3 `components/mcq/Login/Login.vue` — 1 edit

| Line | Original | Change |
|---|---|---|
| 21 | `await login(options, "dashboard");` | `await login(options, "mcq");` |

### 4.4 `components/mcq/Dashboard/Dashboard.vue` — **0 edits** ✅

Because the merged router keeps the path `/mcq/:schema` **identical** to SmartSolver's, both
`router.push('/mcq/0625_s25_22')` and `<router-link to="/mcq/0625_s25_22">` keep working
verbatim. This is a deliberate constraint on the route design (§7.1).

### 4.5 `src/lib/**` (62 files) — **0 edits** ✅

All imports are `@/lib/…`, `../…`, `pdfjs-dist`, `lucide`, or `vue`. All resolve unchanged
under the host's alias. This is the bulk of the codebase and it moves untouched.

### 4.6 Deliberately **not** fixed during the merge

These are pre-existing SmartSolver behaviours. Changing them would violate "preserve
almost exactly". Log them as follow-ups; do not touch them in the merge commit.

1. **pdf.js version split.** `public/build/pdf.js` is **v3.2.146**; the npm `pdfjs-dist` is
   **v5.4.394**. `MCQNav.vue` creates the document with the *iframe's* v3 `pdfjsLib`, then
   `lib/pdf/extractGraphics.ts` and `graphicsToBoundingBoxes.ts` compare that v3 operator
   list against **v5's `OPS` enum**. The numeric values are not guaranteed to match across
   those majors, which would silently mis-detect graphics. Real latent bug; out of scope.
2. **`watch()` called outside a component scope.** `lib/render/renderFocusAreas.ts` calls
   `watch(...)` from inside an IntersectionObserver callback, and `renderFocusAreas`/
   `renderHighlights` are re-invoked per visible page, so watchers and DOM nodes accumulate
   on scroll. Real leak; out of scope.
3. **`startFocusAreaTimer` never cleared.** `window.setInterval` with no handle kept, so it
   survives navigation away from `/mcq/:schema`. Out of scope (but see §12 — it is worth a
   `onBeforeUnmount` clear *if* you accept one extra labelled edit).
4. **Missing `try/catch` around `getPDF`** in `onMounted` — an offline/404 rejects an
   unhandled promise and the loading screen sticks on "Loading...". Out of scope.
5. **`endExam` never navigates.** No end screen (`endScreen.vue` is an empty stub). Out of scope.
6. `phosphor-icons` and the `supabase` CLI as runtime deps, `assets/soluer-loader.json`
   unused — do not port the dead deps (§9.1); keep the unused asset for parity.

---

## 5. Product shell & navigation

### 5.1 Information architecture

```
/                       Landing (Cambridge)                  public, chrome:false
/login                  Firebase login (Cambridge)           public, chrome:false
/mcq/login              Supabase login (SmartSolver)         public, chrome:false
/ide                    Pseudocode IDE                       Firebase-gated
/record/:id             Pseudocode IDE, deep link            Firebase-gated
/problems               Pseudocode problem table             Firebase-gated
/learn                  Pseudocode lessons                   Firebase-gated
/mcq                    MCQ dashboard                        Supabase-gated
/mcq/:schema            MCQ exam runner                      Supabase-gated, chrome:false
```

Cambridge's existing paths are **left alone**. Renaming them to `/pseudocode/*` for symmetry
is tempting but would break saved links, the `record` route used by `IdeView`, and the
`cambridge-ide-source:<id>` localStorage keys. If you want the symmetry, do it as a
**separate follow-up commit** with `redirect:` entries for every old path.

### 5.2 Chrome

The host `App.vue` already honours `route.meta.chrome !== false` to hide the topbar — that
mechanism is exactly what the fullscreen MCQ exam runner needs, so `/mcq/:schema` gets
`meta: { chrome: false }` and renders edge-to-edge just as it did standalone.

SmartSolver's `App.vue` sidebar becomes **`components/mcq/McqShell.vue`**, a
`AI-MERGE-NEW` parent-route component used for `/mcq` only. It reproduces the sidebar
markup and consumes `styles/mcq-shell.css` (§6.2). Its nav links point at `/mcq`,
`/mcq/0455_w22_12`, and `/stats` exactly as the original did.

The host topbar gains a product switcher:

```vue
<!-- AI-MERGE: added the MCQ entry point alongside the existing Pseudocode nav. -->
<RouterLink to="/mcq">MCQ</RouterLink>
```

---

## 6. CSS — the highest-risk area

### 6.1 `MCQNav.css` will destroy the host design system if copied as-is

`MCQNav.vue:2` does `import "./MCQNav.css"` from inside `<script setup>`. Vite turns that
into a **global `<style>` injection at module evaluation time**, and it is **never removed**
when the user navigates away. Because `/mcq/:schema` is a lazy route, that stylesheet also
loads **after** `assets/main.css`, so on equal specificity it wins.

What it currently contains:

```css
@import url('…Inter…');
* { margin:0; padding:0; box-sizing:border-box; font-family:'Inter'; }   /* ⚠️ */
body { width:100vw; height:100vh; }                                       /* ⚠️ */
.loading-screen { … }  .heading { … }  .container { … }  .highlight { … }
#pdf-viewer { … }  .button-track { … }  .track-button { … }
```

The `*` rule sets `font-family` **directly on every element**, which beats the host's
inherited `body { font-family: var(--font-body) }`. The result: General Sans and IBM Plex
Mono vanish app-wide, and `margin:0; padding:0` flattens every heading and paragraph in the
Cambridge IDE, Problems table and Learn pages — permanently, for the rest of the session,
on every route, after one visit to an MCQ paper.

**Confirmed no-collision check** — none of `.container`, `.highlight`, `.loading-screen`,
`.heading`, `.button-track`, `.track-button`, `.focus-area` appear anywhere in
`assets/main.css` or the host components. So the *class* rules are safe; only the `*`,
`body`, and bare-element rules are dangerous.

**Resolution — rewrite `MCQNav.css` under a single root class, with every original
declaration preserved:**

```css
/* AI-MERGE: whole file re-scoped under .mcq-root. This stylesheet is imported from
   <script setup>, which makes it GLOBAL and permanent for the session; the original
   `*` reset and `body` sizing would override the Cambridge design system app-wide
   (fonts, margins, padding) on every route after one MCQ visit.
   All declarations are unchanged — only their selectors are prefixed. */

/* AI-MERGE: Inter kept, but self-hosted rather than @import'd from Google Fonts, to match
   the host's font strategy and avoid a render-blocking third-party request.
   Original: @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap'); */
@import '@fontsource/inter/latin-400.css';
@import '@fontsource/inter/latin-500.css';
@import '@fontsource/inter/latin-600.css';

/* AI-MERGE: `* { … }` → `.mcq-root, .mcq-root *`. Original:
   * { margin:0; padding:0; box-sizing:border-box; font-family:'Inter'; } */
.mcq-root, .mcq-root * {
  margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter';
}

/* AI-MERGE: `body { width:100vw; height:100vh }` → the MCQ root element.
   The host <body> is shared with the Pseudocode app and must not be pinned to the viewport. */
.mcq-root { width: 100%; height: 100%; }

.mcq-root .loading-screen { /* …unchanged… */ }
.mcq-root .heading        { /* …unchanged… */ }
.mcq-root #pdf-viewer     { /* …unchanged… */ }
.mcq-root .container      { /* …unchanged… */ }
/* .button-track / .track-button / .highlight are rendered INTO the iframe document
   and must stay UNPREFIXED — see the note below. */
```

**Critical caveat.** `.button-track`, `.track-button` and `.highlight` style elements that
`renderTracks` / `renderHighlights` append **inside the pdf.js iframe's document**, not the
host document. Prefixing them with `.mcq-root` would silently kill all MCQ styling.

Two options — **pick option A**:

- **A (recommended).** Move those three rule-sets into the `style.textContent` block that
  `MCQNav.vue` already injects into the iframe (`MCQNav.vue:96–118`). That block already
  carries `.highlight`, `.focus-area`, `.focus-area-timer`; adding `.button-track` and
  `.track-button` puts *all* iframe styling in one place and lets the host-side file be
  prefixed wholesale with no exceptions. One labelled edit inside the existing string.
- **B.** Split `MCQNav.css` into `mcq-host.css` (prefixed) and `mcq-iframe.css` (raw text,
  imported with `?raw` and injected). More faithful to the file layout, more machinery.

Note the current duplication either way: `.highlight` is defined **twice** — once in
`MCQNav.css` (host document, `--highlight-color` custom property, hover state) and once in
the injected iframe string (position/cursor/z-index). Only the injected copy can reach the
rendered nodes. Preserve both; do not "clean up".

### 6.2 `style.css` and `Dashboard.css`

- `src/style.css` → `src/styles/mcq-shell.css`, imported **only** by `McqShell.vue` inside a
  `<style scoped>`-adjacent import or directly in the shell. Its `.app-container { height:100vh }`
  must become `height: 100%` (labelled) because the host topbar now sits above it —
  `100vh` would push the sidebar below the fold.
- `Dashboard.css` — one labelled edit: `.router-link { … }` is dangerously generic. Vue does
  not emit a `router-link` class, but `router-link-active` / `router-link-exact-active` are
  emitted app-wide and `assets/main.css:194` already styles `.topbar nav a.router-link-active`.
  The class here is author-applied and only used inside `Dashboard.vue`, so scope it:
  `.dashboard .router-link { … }`.

### 6.3 ⚠️ `X-Frame-Options: DENY` blocks the PDF viewer in production

Both deploy configs send `X-Frame-Options: DENY` on every response:

- `vercel.json` → `headers[0].source: "/(.*)"`
- `firebase.json` → `hosting.headers[0].source: "**"`

`DENY` blocks framing **including same-origin**. The MCQ runner's entire UX is
`<iframe src="/web/viewer.html">` — **same-origin, but still blocked.** This works today in
SmartSolver only because its standalone dev server sends no such header. It will fail the
moment the merged app is deployed, and it will fail *silently* (blank iframe, no console
error in some browsers).

**Resolution (required, in both files):**

```jsonc
// AI-MERGE: DENY → SAMEORIGIN. The MCQ runner frames /web/viewer.html from the same
// origin, and DENY blocks framing even for same-origin documents.
{ "key": "X-Frame-Options", "value": "SAMEORIGIN" }
```

Consider adding `Content-Security-Policy: frame-ancestors 'self'` alongside it — that is the
modern equivalent and keeps the clickjacking protection the original header intended.

### 6.4 Theming (deferred, not blocking)

SmartSolver hardcodes `#007BFF`, `#3498db`, `#2980b9`, `#121212`, `white`, and RGB literals
in `selectOption.ts` (`rgb(0,255,0)` correct / `rgb(255,0,0)` eliminated / `rgb(255,255,0)` neutral).
It has no dark mode. Under the host's `[data-theme='dark']` the MCQ dashboard will look
out of place. **Do not fix this in the merge** — it would touch `selectOption.ts`, which is
otherwise a zero-edit file. Track it as: "retheme MCQ surfaces onto `--accent`/`--panel`/
`--success`/`--danger` tokens."

Note also the host's aggressive normaliser at `main.css:74–100`:
`[data-theme] :is(button, input, textarea, …) { border-radius: 0 !important; box-shadow: none !important; }`.
That `:is()` list is explicit and does **not** include any MCQ class, so MCQ buttons keep
their rounded corners — an intentional non-effect, worth knowing before someone "fixes" it.

---

## 7. Router unification

### 7.1 Route table (host `src/router/index.js`)

```js
// AI-MERGE: MCQ routes ported from SmartSolver src/router.ts. The path "/mcq/:schema" is
// kept CHARACTER-IDENTICAL to the original so Dashboard.vue's router-link and router.push
// calls need no edit at all.
{
  path: '/mcq',
  component: () => import('@/components/mcq/McqShell.vue'),
  meta: { authProvider: 'supabase' },
  children: [
    { path: '', name: 'mcq-dashboard', component: () => import('@/components/mcq/Dashboard/Dashboard.vue') },
  ],
},
{
  path: '/mcq/login',
  name: 'mcq-login',
  component: () => import('@/components/mcq/Login/Login.vue'),
  meta: { public: true, chrome: false },
},
{
  path: '/mcq/:schema',
  name: 'mcq-exam',
  component: () => import('@/components/mcq/MCQNavigator/MCQNav.vue'),
  props: true,
  meta: { authProvider: 'supabase', chrome: false },
},
```

**Ordering matters.** `/mcq/login` must be declared **before** `/mcq/:schema`, otherwise
`:schema` swallows it. (vue-router 5 ranks static segments above params, so this is belt-and-braces —
but declare it first anyway so the intent is readable.)

`props: true` and `defineProps<{schema: string}>()` are both unchanged from SmartSolver.

### 7.2 History mode: keep **hash**

The host uses `createWebHashHistory` and `base: './'` in `vite.config.js`. That pairing is
deliberate: relative asset URLs + a hash router mean the SPA works with **no server rewrite
rules**, which is why `vercel.json` has none. SmartSolver's `createWebHistory` would require:
adding SPA rewrites to `vercel.json`, and changing `base` from `'./'` to `'/'` (relative base
breaks on deep history paths). That is a change to the *host's* deployment contract for the
benefit of the guest.

**Decision: the merged router stays on `createWebHashHistory`.** Consequences to handle:

1. **`useAuth.ts:30` `redirectTo`** must become hash-aware (§4.2).
2. **⚠️ Supabase OAuth implicit flow collides with hash routing.** `@supabase/supabase-js` v2
   returns implicit-flow tokens in the **URL fragment** (`#access_token=…&refresh_token=…`),
   which is precisely where the hash router reads its route from. The two will fight:
   vue-router will try to route to `/access_token=…` and `detectSessionInUrl` may not fire.

   **Resolution — set the PKCE flow explicitly** in the shared client, which returns
   `?code=…` as a *query* param instead:

   ```ts
   // AI-MERGE-NEW: single shared Supabase client. flowType 'pkce' is REQUIRED because the
   // merged app uses hash-based routing — implicit-flow tokens arrive in the URL fragment
   // and would collide with the router's own hash.
   export const supabase = createClient(url, key, {
     auth: { flowType: 'pkce', detectSessionInUrl: true },
   })
   ```

   **Verify before relying on this** (the default differs across supabase-js minors):
   ```bash
   node -e "const {createClient}=require('@supabase/supabase-js');
            console.log(createClient('http://x','k').auth.flowType)"
   ```
   Email/password login is unaffected either way — only OAuth is at risk. Add every
   `redirectTo` URL you produce to the Supabase project's allow-list.

3. `scrollBehavior`'s `to.hash` branch in the host router is about *anchor* hashes; under
   hash history that is the segment after a second `#`. Unchanged behaviour, no action.

### 7.3 vue-router 4 → 5

Verified against the installed `vue-router@5.2.0`: `createRouter`, `createWebHistory`,
`createWebHashHistory`, `useRouter`, `useRoute`, `RouterLink`, `RouterView` are all still
exported. SmartSolver uses nothing beyond `createRouter`/`createWebHistory`/`useRouter`/
`router.push`/`props: true`/`<router-link>`/`<router-view>`. **No v5 migration work.**

---

## 8. Auth — two providers, one guard

The host guard (`router/index.js:46–60`) currently is: *everything that is not
`meta.public` requires a Firebase user, after awaiting `authReady`.* Dropped in as-is, it
would bounce every MCQ route to the Firebase `/login`.

**Recommended (Option B below): make the guard provider-aware.**

- **Option A — mark MCQ routes `public: true`.** One line, zero risk to the host, but it
  removes route-level protection for MCQ. `MCQNav.vue:78–81` still self-guards
  (`if (session == null) router.push("/login")`), so the app is not *unprotected* — but the
  Dashboard is, and the fallback pushes to the **Firebase** login, which cannot produce a
  Supabase session. Dead end.

- **Option B — `meta.authProvider` (recommended).**

  ```js
  // AI-MERGE: the guard is now provider-aware. Pseudocode routes gate on Firebase (default);
  // MCQ routes gate on the Supabase session. Original: a single Firebase check for every
  // non-public route.
  router.beforeEach(async (to) => {
    if (to.meta.public) return true

    if (to.meta.authProvider === 'supabase') {
      const auth = useAuthStore()
      await auth.ready                       // see the note below
      return auth.session ? true : { name: 'mcq-login', query: { redirect: to.fullPath } }
    }

    await authReady
    if (!currentUser.value) return { name: 'login', query: { redirect: to.fullPath } }
    return true
  })
  ```

  **`useAuth.ts` has no `ready` promise** — `init()` is `async` but nothing is awaitable from
  outside, so a hard reload onto `/mcq` would race `getSession()` and bounce a signed-in user
  to the login screen. This is the *one* place where preserving SmartSolver exactly and
  making the merged app correct are in tension. Two ways out:

  1. **Zero-edit workaround:** call `await useAuthStore().init()` in `main.js` *before*
     `app.use(router)`/`mount`, and have the guard read `auth.session` directly. Slight
     startup delay for all routes; no SmartSolver edit at all. **Prefer this.**
  2. **One extra labelled edit:** add an exported `ready` promise to `useAuth.ts` that
     resolves after the first `getSession()`. Cleaner, but a fourth edit to that file.

  Then `MCQNav.vue:79`'s `router.push("/login")` becomes reachable only in edge cases; leave
  it, or make it a 6th labelled edit to `/mcq/login`. Recommendation: **make it the 6th edit** —
  pushing to the Firebase login from the MCQ runner is a genuine dead end for the user.

**Two identities, one browser.** Post-merge a user can be signed into Firebase and not
Supabase, or vice versa. The topbar must reflect that honestly: show the Firebase identity
under Pseudocode routes and the Supabase identity under MCQ routes, rather than one
"Sign out" button that only clears half the session. Small `App.vue` change, and the natural
seam for the future single-identity consolidation (§13).

---

## 9. Toolchain

### 9.1 `package.json` (root) — add

```jsonc
"dependencies": {
  "@supabase/supabase-js": "^2.84.0",   // MCQ auth + table writes
  "pdfjs-dist": "^5.4.394",             // lib/pdf text + graphics extraction
  "lucide": "^0.554.0",                 // track button icons (createElement API)
  "pinia": "^3.0.4",                    // useAuth store
  "@fontsource/inter": "^5.x"           // §6.1, replaces the Google Fonts @import
},
"devDependencies": {
  "sass-embedded": "^1.93.3",           // MCQNav.vue uses <style lang="scss">
  "typescript": "~5.9.3",
  "vue-tsc": "^3.1.3",
  "@vue/tsconfig": "^0.8.1",
  "@types/node": "^24.10.0"
}
```

**Do not port:** `phosphor-icons` (no importer), `supabase` (that is the CLI — install it
globally or as a devDependency if you want `supabase start`), `vue`/`vue-router`/`vite`/
`@vitejs/plugin-vue` (host versions win).

Watch: `lucide` (the framework-agnostic package with `createElement`) is what
`renderTrackButton.ts` uses — **not** `lucide-vue-next`. The stray `SmartSolver/package.json`
lists `lucide-vue-next`; ignore it.

`pdfjs-dist` v5 is imported for `Util`, `OPS` and types only — `getDocument` is never called
from the npm copy (`MCQNav.vue` uses the iframe's v3 `pdfjsLib`), so **no `workerSrc`
configuration is needed**. Vite may still emit a worker chunk; harmless.

### 9.2 `src/main.js` — 2 additions

```js
// AI-MERGE: Pinia added for the MCQ auth store (ported from SmartSolver src/main.ts).
import { createPinia } from 'pinia'
// AI-MERGE: SmartSolver's App.vue called useAuthStore().init() on mount; the merged App.vue
// is the Cambridge shell, so the Supabase session is restored here instead — and awaited,
// so the router guard never races it on a hard reload onto /mcq (§8).
import { useAuthStore } from '@/stores/useAuth'

const app = createApp(App)
app.use(createPinia())
initializeTheme()
await useAuthStore().init()
app.use(router)
app.mount('#app')
```

Top-level `await` in `main.js` is fine (ES module, Vite target supports it). If you would
rather not block first paint, mount first and let the guard await `auth.ready` (§8 option 2).

### 9.3 TypeScript

`src/website/frontend/` currently has `jsconfig.json`. Having both `jsconfig.json` and
`tsconfig.json` in one directory confuses editors and `vue-tsc`. **Replace** it:

```jsonc
// src/website/frontend/tsconfig.json — AI-MERGE-NEW: replaces jsconfig.json so the ported
// TypeScript MCQ code type-checks while the existing JavaScript keeps working untouched.
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "types": ["vite/client"],
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "allowJs": true,
    "checkJs": false,          // the host app is untyped JS; do not start type-checking it now
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "src/**/*.js", "../../../supabase/functions/**/*.ts"]
}
```

**Do not add `vue-tsc` to the root `build` script.** SmartSolver's `build` was
`vue-tsc -b && vite build`, and its `noUnusedLocals`/`noUnusedParameters` are strict; the code
has never been type-checked in this checkout (no `node_modules`). Wiring it into the deploy
build risks failing Vercel on pre-existing guest type errors. Add a **separate, non-blocking**
script instead:

```json
"typecheck": "vue-tsc --noEmit -p src/website/frontend/tsconfig.json"
```

Run it once during the merge, record the failures, and fix them in a follow-up — not in the
merge commit.

Vite transpiles `.ts` via esbuild with no type checking, so **the app builds and runs
regardless of `typecheck` output.**

### 9.4 `index.html`

- Title: `Pseudocode — Cambridge 9618 Practice` → something that covers both products
  (e.g. `Cambridge Practice — Pseudocode & MCQ`). One line.
- The pre-paint theme bootstrap and `data-theme-storage="cambridge-ide-theme"` stay as-is.
- Do **not** add the Inter `<link>` here — §6.1 self-hosts it via `@fontsource/inter` so it
  only loads on MCQ routes.
- The guest's `index.html` (`my-vue-app`, `/vite.svg`) is discarded entirely.

### 9.5 `vite.config.js`

**No functional change is required.** `@vitejs/plugin-vue` handles `lang="ts"` SFCs, esbuild
handles `.ts`, `sass-embedded` is auto-detected for `lang="scss"`, and the `@` alias already
points where the guest code expects. Two optional additions:

```js
// AI-MERGE: pdfjs-dist ships a large ESM build; pre-bundling it keeps dev-server cold starts
// reasonable now that the MCQ route imports it.
optimizeDeps: { include: ['pdfjs-dist'] },
```

and, if the build warns about chunk size, a `build.rollupOptions.output.manualChunks` entry
splitting `pdfjs-dist` and `@supabase/supabase-js` out of the main bundle.

The existing `gradingApiPlugin` dev middleware is untouched and keeps serving `/api/grade`.

---

## 10. Assets & deployment

### 10.1 The 16 MB pdf.js bundle

`public/web/` (7.1 MB) + `public/build/` (9.2 MB) must be copied verbatim into
`src/website/frontend/public/`. `viewer.html` loads `../build/pdf.js` and `viewer.css`
**relatively**, so the two folders must stay siblings — do not flatten or rename them.

Roughly half that size is `.map` files (`pdf.js.map`, `pdf.worker.js.map`,
`pdf.sandbox.js.map`, `viewer.js.map`). Dropping them would halve the payload, but they are
never served unless devtools asks. **Copy everything verbatim** — trimming is a separate
decision, and `viewer.js` references its map by name.

**⚠️ `.gitignore` conflict.** The root `.gitignore` has a blanket `*.png` / `*.jpg` rule with
explicit `!src/website/frontend/public/resources/images/` un-ignores. `public/web/images/`
contains the pdf.js toolbar icons. **Add matching un-ignore lines** or the viewer ships with
missing icons:

```gitignore
# AI-MERGE: vendored pdf.js viewer icons must be tracked (blanket *.png rule above).
!src/website/frontend/public/web/images/
!src/website/frontend/public/web/images/*.png
```

Also confirm `public/build/` is not caught by any `build/`-style ignore. Verify the whole
copy with:

```bash
git status --porcelain src/website/frontend/public/web src/website/frontend/public/build | wc -l
git check-ignore -v $(find src/website/frontend/public/web -name '*.png' | head)
```

### 10.2 `vercel.json`

1. `X-Frame-Options: DENY` → `SAMEORIGIN` (§6.3) — **required**.
2. `functions["api/grade.py"].excludeFiles` — add the new heavy directories so the Python
   Function bundle does not swell by 16 MB:
   ```jsonc
   // AI-MERGE: keep the vendored pdf.js viewer out of the /api/grade Function bundle.
   "excludeFiles": "{tests/**,functions/**,resources/**,pseudocode_writing_hits/**,qp_output/**,ms_output/**,normalize/**,SmartSolver/**,src/website/frontend/public/web/**,src/website/frontend/public/build/**,src/website/frontend/public/resources/images/**}"
   ```
3. `buildCommand: "npm run build"` and `outputDirectory: "src/website/static"` are unchanged.
4. No SPA rewrites needed — hash routing (§7.2).

### 10.3 Origins & CORS

`/api/grade` is same-origin (Vercel Function). The Supabase edge function is **cross-origin**
(a `*.supabase.co` host in production). `fetch-pdf/index.ts` currently sets no CORS headers
and has no `OPTIONS` handler — it worked from `localhost:5173` → `localhost:54321` only
because that request is a simple-ish POST... but it sends `Content-Type: application/json`
and `Authorization`, which **forces a preflight**. Expect this to fail cross-origin.

**Action (edge function, guest code — label it):** add an `OPTIONS` branch returning
`Access-Control-Allow-Origin`, `-Headers: authorization, content-type`, `-Methods: POST, OPTIONS`,
and echo `Access-Control-Allow-Origin` on the 200/4xx/5xx responses. This is a genuine
deployment blocker for the MCQ product, independent of the DB question.

Also note the response is `Content-Type: application/pdf` while the body is **JSON**
(`{qp: number[], answers}`) — pre-existing, harmless, do not "fix" during the merge.

Sending the PDF as a JSON array of bytes inflates a ~1 MB PDF to ~4 MB of text. Pre-existing;
follow-up, not merge work.

### 10.4 `firebase.json`

`hosting.site` is literally `"smartsolver"` — the Firebase Hosting site for the *Cambridge*
app is already named that. Coincidence, but confusing post-merge; leave it (renaming a
Hosting site is a console operation) and add a comment in the README. Apply the same
`X-Frame-Options` fix here (§6.3). `public: "src/website/static"` and the `**` → `/index.html`
rewrite already serve `/web/viewer.html` correctly (Hosting matches real files first).

### 10.5 Supabase local stack

Move `SmartSolver/smartsolver/supabase/` → repo-root `supabase/` and add to the root
`package.json`:

```json
"mcq:supabase": "supabase start",
"mcq:functions": "supabase functions serve fetch-pdf"
```

Add `.env.local` entries (and Vercel Project env vars) for:
`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`. The `sb_publishable_…` key currently hardcoded
is a *publishable* key and safe in the bundle, but it points at `127.0.0.1` and must be
env-driven for any real deploy.

---

## 11. Phased execution plan

Each phase ends in a **runnable app**. Do not batch them.

### Phase 0 — Safety net
```bash
git add -A && git commit -m "checkpoint before SmartSolver merge"   # SmartSolver/ is untracked today
git checkout -b merge/smartsolver
cd SmartSolver/smartsolver && npm install && npm run dev   # baseline: does the guest even run?
```
Record the baseline. If the guest does not run standalone, you cannot tell merge breakage
from pre-existing breakage. Given the absent `node_modules`, **assume it does not** until proven.

### Phase 1 — Dependencies & toolchain (no behaviour change)
- Add deps (§9.1), replace `jsconfig.json` with `tsconfig.json` (§9.3), add `typecheck` script.
- **Verify:** `npm run build:website` still succeeds; `npm run test:frontend` still passes;
  the Pseudocode app is visually and functionally identical.

### Phase 2 — Assets
- Copy `public/web/` + `public/build/`; fix `.gitignore` (§10.1).
- **Verify:** `npm run dev:website`, open `http://localhost:5173/web/viewer.html` directly —
  the stock pdf.js sample PDF must render. This isolates asset/path problems from app problems.

### Phase 3 — The zero-edit code (`src/lib/**`, stubs, assets)
- Copy `lib/`, `assets/soluer-loader.json`, the empty stubs.
- **Verify:** `diff -r` against the source is empty; `npm run build` succeeds (tree-shaken out,
  nothing imports it yet); `npm run typecheck` output recorded as the guest-code baseline.

### Phase 4 — Supabase client + auth store
- New `src/services/supabase.js` (§7.2, PKCE); copy `stores/useAuth.ts` with its 3 labelled edits.
- Pinia + `await init()` in `main.js` (§9.2).
- **Verify:** app boots, Pseudocode routes unaffected, no Supabase errors in console with the
  local stack down (the store must degrade quietly).

### Phase 5 — MCQ components + CSS isolation ← **the risky phase**
- Copy the four component folders; rewrite `MCQNav.css` per §6.1; move the iframe rules into
  the injected style block (option A); scope `Dashboard.css`; create `McqShell.vue` and
  `styles/mcq-shell.css`.
- **Verify — the regression that matters:** load `/mcq`, then navigate to `/ide`, `/problems`,
  `/learn`, `/`. **Fonts, margins and padding must be unchanged from Phase 0.** Screenshot-diff
  the landing page before and after if you can. This is the single highest-value check in the
  whole plan.

### Phase 6 — Router + guard + chrome
- MCQ routes (§7.1), provider-aware guard (§8), topbar entry + identity display (§5.2).
- **Verify:** `/mcq` gates correctly, `/mcq/:schema` renders fullscreen with no topbar,
  every Pseudocode route still gates on Firebase, a hard reload onto `/mcq` while signed in
  does not bounce.

### Phase 7 — Deployment configs
- `X-Frame-Options` in both files (§6.3), `excludeFiles` (§10.2), edge-function CORS (§10.3),
  move `supabase/`, add env vars and scripts.
- **Verify:** deploy to a Vercel **preview**; confirm the iframe frames (this cannot be
  verified locally — the header is not sent by the dev server).

### Phase 8 — Cleanup & docs
- Delete `SmartSolver/` (or move to `archive/`); keep `cards/` and `dashboard/` out of the merge
  or archive them separately. **`call_fetch_pdf.sh` must not be committed with credentials.**
- Update `README.md` (a "Two products" section), `AGENTS.md` (`src/website/frontend/src/lib`
  and `components/mcq` now exist and are TypeScript), and `docs/project_direction.md`.
- Rotate the Supabase test account password that was in `call_fetch_pdf.sh`.

---

## 12. Verification checklist

**Merge fidelity**
- [ ] `diff -r SmartSolver/smartsolver/src/lib src/website/frontend/src/lib` is empty
- [ ] Every file that differs from its SmartSolver original contains an `AI-MERGE` marker
- [ ] `grep -rn "AI-MERGE" src/website/frontend/src | wc -l` matches the change count in §4
- [ ] No `AI-MERGE` marker appears in a file that is byte-identical to its original

**Host regression (run before and after Phase 5)**
- [ ] `/`, `/login`, `/ide`, `/record/:id`, `/problems`, `/learn` render identically
- [ ] Body font is still General Sans; code font is still IBM Plex Mono
- [ ] Light/dark toggle works on every route, including after visiting `/mcq`
- [ ] `npm run test:frontend` passes
- [ ] `python -m unittest discover -s tests -p 'test_*.py'` passes (untouched, but cheap insurance)
- [ ] Firebase sign-in → `/ide` → Run (wasm) → Submit (`/api/grade`) end-to-end

**MCQ functionality (parity with standalone SmartSolver)**
- [ ] `/mcq/login` signs in via email and via Google OAuth (watch the hash/PKCE issue, §7.2)
- [ ] `/mcq` dashboard links navigate to `/mcq/0625_s25_22`
- [ ] PDF loads in the iframe; "Loaded!" appears; Start Exam reveals the paper
- [ ] Option highlights render on every page and follow scroll
- [ ] `C` / `E` toggle mode from **both** the host window and inside the iframe
- [ ] Clicking an option cycles neutral → correct/eliminated; only one "correct" per question
- [ ] Focus-area timer increments on the clicked question only
- [ ] Copy/Flag/Star/Save track buttons toggle and log
- [ ] Zooming the PDF rescales highlights, focus areas and tracks (`observePDFScaleChanges`)
- [ ] End Exam writes one `exam_attempts` row and N `question_attempts` rows
- [ ] `enrichAnalytics` output (confidence/difficulty/interest) matches the standalone app for
      an identical interaction script — **capture a golden JSON in Phase 0 to compare against**

**Production-only**
- [ ] Preview deploy: iframe is not blocked (`X-Frame-Options`)
- [ ] Preview deploy: `fetch-pdf` preflight succeeds cross-origin
- [ ] `/api/grade` Function bundle has not grown (check the Vercel build log's function size)

---

## 13. Deferred: the database question (owner's task)

This plan leaves **both** data layers running unchanged. Everything a future consolidation
must touch is listed here so it is a bounded job, not an archaeology exercise.

**Firebase surface (Pseudocode)**
- `src/website/frontend/src/services/firebase.js` — app/auth/RTDB/analytics init
- `src/website/frontend/src/services/auth.js` — `currentUser`, `authReady`, sign-in helpers
- `src/website/frontend/src/services/userProgress.js` — `users/$uid/{profile,progress,stats}`
- `database.rules.json` — RTDB rules, incl. `gradingQuotas/$uid`
- `api/grade.py` — validates the Firebase ID token via `identitytoolkit accounts:lookup`
- `api/_quota.py` — reads/writes `gradingQuotas/$uid` over the RTDB REST API with that token

**Supabase surface (MCQ)**
- `src/website/frontend/src/services/supabase.js` *(new, §7.2)* — the single client
- `src/website/frontend/src/stores/useAuth.ts` — session, login, logout
- `src/website/frontend/src/lib/supabase/{pushToExamTable,pushToAttemptsTable,lettersToMask,letterToIndex}.ts`
- `supabase/schema.sql` — `attempts`, `exam_attempts`, `question_attempts`
- `supabase/functions/fetch-pdf/` — Deno edge function

**Notes for whichever direction you consolidate**
- `schema.sql` defines **no RLS policies**. Under Supabase's default-deny that means those
  tables are unreadable from the client today — the inserts work only because the local dev
  stack is permissive. Whatever you choose, RLS on `user_id` is required.
- `attempts` (generic `attempt_type` + `metadata jsonb`) is unused by the code; only
  `exam_attempts` and `question_attempts` are written.
- `question_attempts.selected_option` is `check between 0 and 3` — hardcoded four-option MCQ.
- The natural join key between the two worlds is the user identity, and there is currently
  **none**. Deciding that (one Firebase identity with a Supabase JWT bridge? one Supabase
  identity with Firebase dropped? a `user_links` table?) is the actual decision; the rest is
  mechanical. §8's "two identities, one browser" topbar is the seam where it surfaces.
- If you consolidate onto Supabase, `api/grade.py`'s Firebase token validation and
  `api/_quota.py`'s RTDB quota storage both need replacing — that is Python work on the
  Vercel Function, not frontend work, and it is the largest single item in the DB migration.

---

## 14. Risk register

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| MCQ global CSS silently degrades the Pseudocode UI | **High** | Certain if copied as-is | §6.1 rewrite + the Phase 5 cross-route visual check |
| `X-Frame-Options: DENY` blanks the PDF viewer in prod | **High** | Certain | §6.3; cannot be caught locally — needs a preview deploy |
| Supabase OAuth hash collides with hash routing | **High** | Likely | §7.2 PKCE + verify `flowType` on the installed version |
| `fetch-pdf` CORS preflight fails cross-origin | **High** | Likely | §10.3 — add OPTIONS + ACAO headers |
| Guest code has never been built here (no `node_modules`) | Medium | — | Phase 0 baseline; treat any failure found as pre-existing, not merge-caused |
| pdf.js v3 viewer vs v5 `OPS` enum mismatch | Medium | Unknown | §4.6 — log, do not fix during the merge |
| `vue-tsc` in the build fails Vercel on guest type errors | Medium | Likely | §9.3 — keep `typecheck` out of `build` |
| `.gitignore` `*.png` swallows pdf.js viewer icons | Medium | Certain | §10.1 un-ignore lines + `git check-ignore` verification |
| Credentials in `call_fetch_pdf.sh` reach git history | Medium | Certain if copied | §3 — do not commit; rotate the password |
| `startFocusAreaTimer` interval survives route change | Low | Certain | §4.6 — pre-existing; one optional labelled edit |
| Bundle size / cold start from `pdfjs-dist` on the MCQ route | Low | Likely | Lazy route (already) + optional `manualChunks` (§9.5) |
| MCQ surfaces look wrong in dark mode | Low | Certain | §6.4 — deferred by design |

---

## 15. Summary of the diff you should expect

| Category | Files | Lines changed in SmartSolver code |
|---|---|---|
| Copied **verbatim** (no marker) | 62 (`lib/**`) + 4 stubs + 1 asset + ~40 pdf.js assets | **0** |
| Copied with labelled edits | `MCQNav.vue` (5–6), `useAuth.ts` (3), `Login.vue` (1), `Dashboard.css` (1), `MCQNav.css` (selector rewrite), `mcq-shell.css` (1) | **~12 statements + 1 stylesheet re-scope** |
| New files (`AI-MERGE-NEW`) | `services/supabase.js`, `components/mcq/McqShell.vue`, `tsconfig.json` | — |
| Host files modified | `main.js`, `App.vue`, `router/index.js`, `index.html`, `package.json`, `vite.config.js`, `vercel.json`, `firebase.json`, `.gitignore` | — |
| Discarded | guest `main.ts`, `router.ts`, `App.vue`, `index.html`, `vite.config.ts`, `tsconfig*`, `package*.json`, `Landing Page/`, `call_fetch_pdf.sh` | — |

**Roughly 97% of SmartSolver's application code moves untouched.** The functionality-bearing
core — PDF parsing, option detection, highlighting, focus-area timing, event logging, and the
entire analytics model in `enrichAnalytics.ts` — is not modified at all.
