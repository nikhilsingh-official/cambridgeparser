<!-- ==========================================================================
     Documentation only. The single outstanding-work list for cambridgeparser.com,
     covering both the pseudocode IDE and the Soluer paper solver.

     Companions, all still authoritative in their own scope:
       docs/project_direction.md        the pipeline's architecture and intent
       docs/grading_roadmap.md          the AST-grading phase plan
       apps/solver/docs/future_work.md  per-defect detail behind Part B
       apps/solver/docs/database_design.md  the schema's rationale, incl. RLS drafts
     ========================================================================== -->

# CambridgeParser — Roadmap

**What exists.** Two working applications and a pipeline that feeds one of them.

- **The pseudocode IDE** (`src/website/`) — landing, login, problem explorer,
  CodeMirror editor over a wasm build of the Rust parser, and model grading via
  `/api/grade` on Vercel. Deployed. Firebase Auth, Firebase Realtime Database.
- **Soluer** (`apps/solver/`) — the MCQ paper solver. Highlight and eliminate
  options directly on the PDF, timed focus areas, full event recording, an
  end-of-exam summary that writes to Supabase. Runs locally only.
- **The pipeline** (`src/pipeline/`) — 118 segmented question papers, 119 mark
  schemes, 176 assembled records, all deterministic and tested (257 tests).

**What does not exist yet is a *site*.** The two apps share a name, a palette,
and a login *design* — and nothing else. They have separate identity providers,
separate databases, separate deploy targets, and no routing between them. Part A
is that gap. Parts B and C are each app's own backlog.

Ordering is at the end (Part E). Read that first if you want to know what to do next.

---

## Part A — What blocks a unified cambridgeparser.com

### A1. One identity. *This is the whole merge.*

The IDE authenticates with **Firebase Auth** and stores progress in the Firebase
Realtime Database under `users/$uid/`. Soluer authenticates with **Supabase Auth**
and stores attempts in Postgres keyed on `auth.uid()`. A user who signs into both
today is two different people with two different progress histories.

The login *pages* were unified (commit `2d43044`), which makes them look like one
product and hides that they are not. That cosmetic fix has bought time, not a
solution.

`apps/solver/docs/future_work.md` §6.2 already records the decision that the IDE
moves to Supabase. That is the right call — Postgres is where the analytical work
already lives, and Firebase RTDB cannot express any of the stats views — but it
has not started. It requires:

| Step | Notes |
|---|---|
| Port `services/auth.js` and `LoginView.vue` to `@supabase/supabase-js` | The solver's `stores/useAuth.ts` is the model; it already handles `authReady`, OAuth, and password reset |
| Design `pseudocode_attempts` | Per §6.2, a **sibling** of `exam_attempts`, not a reuse of it. Marking-point-level results do not fit a per-question MCQ row |
| Migrate the RTDB `users/$uid/progress/` subtree | Small and shallow by design; a one-off script, but the uid mapping is the hard part — Firebase uids do not survive |
| Re-point `/api/grade`'s token check | It validates a Firebase ID token today (`api/grade.py`) and enforces quotas via `gradingQuotas/$uid` in RTDB. Both move to Supabase JWT + a Postgres quota table |
| Retire `firebase.json`, `database.rules.json`, `.firebaserc` | Note the hosting site is still named `smartsolver`, from before the rename |

**Do not deploy Soluer publicly before this.** Two live auth systems on one
domain is a much worse problem to unwind than one un-deployed app.

### A2. One deployment

`apps/solver/` has **no deployment configuration at all** — no `vercel.json`, no
build target, no environment plumbing. The root `vercel.json` builds only the IDE.

Decide the URL shape first, because it determines the rest:

- `cambridgeparser.com/solver/*` — one Vercel project, needs the solver built to
  a sub-path (`base` in `vite.config.ts`) and a rewrite. Shared cookies, so A1
  gets easier.
- `solver.cambridgeparser.com` — two projects, independent deploys, but the
  Supabase session has to be shared across subdomains deliberately.

Whichever: the solver's `fetch-pdf` edge function **has no CORS handling** — no
`OPTIONS` branch, no `Access-Control-Allow-*` headers. It works today only
because everything is localhost. It breaks on the first cross-origin deploy.

### A3. One design system — mostly done, not finished

`apps/solver/src/styles/themes.scss` holds the three shared themes
(`soluer-dark`, `exam-paper`, `cambridge-dark`) and the IDE's palettes were
ported into it (`fb794ee`). But the **IDE has not been switched onto it** — it
still owns its own styles under `src/website/frontend/`. Until the tokens are
extracted somewhere both apps import, "shared" means "copied", and they will
drift the first time either changes.

---

## Part B — Soluer

Detail for every item here is in `apps/solver/docs/future_work.md`; this is the
current status and the ordering.

### B1. The schema has never been executed — **blocks everything below it**

`apps/solver/supabase/schema.sql` is 25 kB of DDL that has never run against a
database. No `psql`, `docker`, or `supabase` CLI was available while it was
written. Every view, trigger, and generated column downstream of it is unverified.

```bash
cd apps/solver
supabase db reset
psql "$SUPABASE_DB_URL" -f supabase/seed_subjects.sql   # 196 subjects
```

Expect to fix DDL errors. Check in this order:

1. The five **generated columns** on `exam_attempts` — they assume `split_part`,
   `left`, `right`, `substr` and `::smallint` are all `IMMUTABLE`. Believed
   correct, unproven. Fall back to a `before insert` trigger if Postgres refuses.
2. The `paper_id` `CHECK` regex against your real paper set.
3. `drop table if exists attempts;` runs **last** — confirm it holds nothing.

### B2. RLS — the production gate

Deliberately absent: local emulators only, so far. Supabase default-denies, so
**nothing works in production without it**. Policies are already drafted in
`apps/solver/docs/database_design.md` §3.5.

Every query in `src/lib/supabase/queries/` takes an explicit `userId` and filters
on it. That predicate is currently the *only* thing scoping data to the right
user. Keep it even after RLS lands — defence in depth, and it makes the queries
readable.

One decision to make there: `paper_answers` must be client-readable today, which
means a determined user can read the answer key before answering.

### B3. The stats page is still placeholder data

The whole read layer exists (`src/lib/supabase/queries/` — `attempts`, `activity`,
`focus`, `subjects`, `goals`; every view has a typed reader) and **the UI calls
none of it**. `components_stats/` still renders:

- `StatsPage.vue:10–17` — filters hardcoded to `['Wade Cooper', 'Arlene Mccoy', …]`,
  `['Apple','Banana','Cherry']`, `['Red','Green','Blue']`. Should be years,
  series and variants from `v_attempt_summary`.
- `StatsPage.vue:33` — Lorem ipsum subtitle.
- `StatsPage.vue:56` — `.pie-container` is an empty `div`.
- `CardStrip.vue:4` — a generated `testStats` array.

**No charting library is installed.** `apps/solver/docs/stats_page_design.md` §2
and §8 settled on Apache ECharts, tree-shaken. That decision still stands; the
install has not happened.

### B4. Scores are still forgeable

`cacheAnswerKey.ts` writes the answer key **from the browser**, so a score is
only as trustworthy as the client that reported it. The `fetch-pdf` edge function
already parses the key server-side — it should write it directly and the client
function should be deleted.

This is the last step to unforgeable scores and a **hard prerequisite for any
shared, class, or leaderboard view**. Decide it before the schema hardens: it
changes the `fetch-pdf` contract.

### B5. Unbuilt UI work

Three items were scoped and approved but not started:

| Item | What is missing |
|---|---|
| **Overview rows are inert** | `SideWindowQuestion.vue` renders each question's state correctly but has no click handlers — you cannot jump to a question or answer from the panel. Route it through the same path as `selectOption` so the paper, the event log and `examState` stay consistent |
| **The Copy button does nothing** | `ActiveQuestionButtons.vue` logs the event and stops. No clipboard write. Question text is available from the parsed `segmentQuestions` / `getOptions` output |
| **No shortcut discoverability** | Only `KeyC` / `KeyE` exist (`lib/utils/keydownListeners.ts`) and the only hint is the chip added to the bottom bar. Needs a help overlay, `?` to open |

Also open, from `future_work.md` §5:

- `profiles` is never written. The table exists and nothing upserts it. Do it on
  first sign-in and store the IANA timezone there so it survives a device change.
- `src/lib/pdf/createPDFObservers.ts` has **no importers** and its `renderTracks`
  call has the wrong argument order. Wire it up or delete it.
- `npm run build` runs `vue-tsc -b && vite build` and still fails: **7 errors,
  all `TS6133` unused declarations** (down from 20). They are trivial. Until then
  `npx vite build` is the working build command — which means CI would not catch
  a real type error today.

### B6. Metrics with infrastructure but no consumer

| Metric | State | Needs |
|---|---|---|
| Calibration curve | `v_calibration_curve` written | a chart, and `question_metrics` populated |
| Over/underconfidence | `v_question_flags` written | thresholds validated against real data — 0.7 / 0.4 were **picked, not measured** |
| Guess detection | `v_question_flags` written | same problem: `< 0.4 × median` and `exploration_depth <= 1` are guesses about guessing |
| **Answer-change quality** | not built | **the highest-value unbuilt metric.** `attempt_events` records every transition with its option index, so right→wrong vs wrong→right is now derivable. `optionSwitchCount` only ever counted switches, never whether they helped |
| Elimination precision | not built | `eliminated_mask` × `correct_option` — how often a ruled-out option really was wrong, and how often the *correct* one got eliminated |
| Pacing / fatigue | not built | `attempt_events` gives true answering order, which `question_number` cannot |
| Topic mastery | plumbing done | **content.** `src/constants/topicMap.ts` is a fill-in-the-blank file awaiting a syllabus taxonomy, then `seedTopics()` and `applyPaperTopics()` |
| Exam readiness / predicted grade | not built | a grade-threshold table per subject; thin layer over accuracy + topic mastery |

Once a few hundred questions exist, **check the three thresholds against data**.
A "guess" rule that fires on 40% of questions is measuring reading speed.

### B7. Deferred by choice

- `enrichAnalytics` stays client-side until weights are first retuned; the cost
  lands then, as a client-side backfill rather than one SQL statement.
- Event retention is unbounded. Fine at personal scale. If it stops being fine:
  keep events for the newest N attempts and keep `question_attempts` forever.
- Nothing enforces that changing the weights in `enrichAnalytics.ts` also inserts
  a `metrics_version` 2. It is a convention, and conventions decay — a comment at
  the top of that file is the minimum.

---

## Part C — The IDE and the pipeline

Numbers below were regenerated on 2026-08-19 by re-running
`src.pipeline.analysis.diagnostics.validate_extraction` and
`validate_marking_points`. The artifacts that were checked in before that were
from July and materially out of date — see C5.

**Where the corpus stands.** Better than the old reports suggested.

| Measure | Value |
|---|---|
| Segmented question papers / segments | 118 / 4289 |
| Mark-scheme files | 119 |
| Mark-scheme nodes with answer text | 2392 of 3464 (69%) |
| Final records (from 50 papers) | 176 — 194 assembled, 18 deduplicated, 19 discarded |
| Records **with** marking points | **176 of 176** |
| Records with mark-scheme answer text / screenshots / syllabus tags | 175 / 175 / 176 |
| Marking-point audit severity | **0 high**, 22 medium, 46 low, 108 clean |

Extraction is in good shape. What follows is the edge work and the one large gap.

### C1. The 2015–2016 mark schemes do not parse — **the one large gap**

**22 of 119** mark-scheme files produce empty question lists: every 9608 paper
from `s15`, `w15`, `s16`, `w16`. Mark-scheme parsing is table-first and these
older schemes use a layout it does not handle.

That is roughly a fifth of the mark schemes contributing nothing, and it caps the
corpus at the 50 papers that currently yield records. Treat it as parser coverage
work — the README is explicit that this is **not** a hidden fallback path, so do
not paper over it with a text-mode guess.

The 19 discarded records all fail for the same reason (`ms_question_not_found`),
so expect this to recover some of them too.

### C2. The grading evaluation set was written but never run

`src/pipeline/grading/eval/cases.py` holds **15 hand-authored questions × 3
candidates each** (high / medium / low quality) with human ground-truth marks,
spanning the three answer shapes in the corpus. `grading_eval_results.json` does
not exist — the runner has never produced output.

`docs/grading_roadmap.md` Phase 8 is explicit that this comes *before* bulk use.
Until it runs there is no measured answer to "how good is the grading", only the
model's own confidence. This is the cheapest high-value item in this document:
the cases are already written.

### C3. Extraction noise worth fixing

- **13 segments carry `html_tag_leak`** — raw HTML reaching question text (9608
  `s17` q6/q7, `s18`, `w16`, `w18`, `w19`).
- **58 short segments** — mostly legitimate (`LDM #500 ACC`, `Keyboard`), but
  `9608_s17_qp_13:q1|(a)` is literally `"Describ"`, which is truncation.
- **4 nodes with garbage answer text** — control characters, one repeated-char run.
- **2 unresolved mark-scheme rows** in `9608_s17_ms_21` and `_23`.
- **22 medium-severity marking-point flags**, mostly `declared_max_list` (33
  occurrences) — the extracted points total more than the question's declared
  marks. `apply_max_marks_cap` clamps this at grading time, so it is a reporting
  wart rather than a scoring bug, but it hides genuine over-extraction.

### C4. Generated records store CWD-relative paths — **latent, and it bit once**

`build_final_records._find_screenshot` stores `str(matches[0])` — literally
whatever prefix `--screenshots-dir` was invoked with. Consumers
(`src/website/app.py:_serve_screenshot`, `build_static_resources.py`) then do
`Path(stored_path)` against the current working directory.

Moving the generated tree to the location `src/resources/paths.py` has always
declared therefore broke every screenshot reference at once — 350 of them, silently,
with the full test suite still green because nothing tests the stored paths.
Migrated (see C5), but the fragility is unfixed: **the next relocation breaks it
again, and no test will notice.**

Fix by storing paths relative to `PSEUDOCODE_WRITING_DIR` and joining on read, or
at minimum add a test that resolves a sample of stored screenshot paths.

### C5. The checked-in validation artifacts had drifted

`extraction_validation.json` was from 19 July and `marking_point_validation.json`
from 21 July, while the records they describe were rebuilt on 14 August. The old
reports claimed 192 records with **100 missing marking points**; the truth is 176
records with **none** missing. Anyone planning from those files would have
prioritised a problem that no longer exists.

Both have been regenerated. They are gitignored build outputs, so nothing keeps
them fresh — either regenerate them as part of the records build, or stop treating
them as a record of anything.

### C6. The IDE's own gaps

- **`build:website` cannot run on Vercel.** It needs the corpus and the Rust
  toolchain, so the deployment build only bundles pre-committed artifacts under
  `src/website/frontend/public`. After changing pipeline inputs you must run
  `npm run build:website` locally and commit the regenerated public artifacts and
  `src/website/server_resources/grading_question_records.json.gz`. This is a
  manual step that will be forgotten; it wants a check that fails when the
  committed artifacts are older than their inputs. (Same class of problem as C5.)
- **Learn is partly a stub** — `LearnView.vue:373` renders
  "Syllabus extension · practice coming soon" for topics without practice
  content. See `docs/learn_topic_research.md`.
- One `TODO` in the entire codebase:
  `pseudocode-parser/src/Parser/parser.rs:124` ("should be able to remove the trim").

## Part D — Security and hygiene

| Item | Severity | Action |
|---|---|---|
| **Leaked password** | High | `REMOVED_HISTORICAL_PASSWORD` was hardcoded in `Login.vue` at commit `1857cf2` and removed by `fa220df`. It is **still in git history**, and that history is now in this repository too. It is burned regardless of whether you rewrite history — **rotate the account password**. It also appears in `call_fetch_pdf.sh` in the archived pre-merge tree |
| Emulator keys in history | Low | `supabase/.temp/` was tracked until `5943871`, carrying local service-role and JWT-secret values. They are Supabase's published local defaults, not secrets, but the directory is gitignored now |
| RLS absent | High | Part B2. Blocks production, not development |
| Answer key client-writable | Medium | Part B4 |
| `fetch-pdf` has no CORS | Medium | Part A2. Latent until the first cross-origin deploy |
| `.env` handling | Low | `apps/solver/.env.example` exists; `useAuth.ts` falls back to `http://127.0.0.1:54321`, which is right for dev and wrong to ship. Make the production build fail on a missing `VITE_SUPABASE_URL` rather than silently pointing at localhost |

---

## Part E — Suggested order

Grouped by what unblocks the most, not by size.

**1 — Make Soluer real.** Nothing in Part B can be trusted until the DDL runs.

1. **B1** — `supabase db reset`, fix what breaks, seed the 196 subjects. Every
   other Soluer item is downstream of this.
2. **B5** — the three UI items and the seven `vue-tsc` errors. Small, and they get
   `npm run build` passing, so type errors start being caught instead of skipped.
3. **B3** — install ECharts and wire `components_stats/` to the query layer that
   has been sitting unconsumed since `aec4e13`.

**2 — Make the corpus gradeable.** Independent of the above; can run in parallel.

4. **C2** — run the 15-case evaluation set. The cases are already written; this is
   the cheapest way to learn whether the grading is any good.
5. **C1** — the 2015–2016 mark-scheme layout. The largest single content gap, and
   it should recover some of the 19 discarded records too.
6. **C4** — make stored screenshot paths relocation-proof, or at least tested.
   Do it before the next corpus rebuild, not after.

**3 — Make it one site.** Only worth starting once Soluer is worth deploying.

7. **A1** — port the IDE to Supabase Auth. The largest single piece of work in
   this document; everything about a unified product waits on it.
8. **B4 → B2** — server-side answer key, then RLS. Together these are the gate to
   deploying Soluer publicly at all.
9. **A2** — pick the URL shape, add CORS to `fetch-pdf`, write the solver's deploy
   config (it has none).
10. **A3** — extract the shared design tokens so the two apps stop drifting.

**Do at any point, cheaply:** rotate the leaked password (Part D — **today**);
add the `metrics_version` comment (B7); decide whether the validation artifacts
are generated as part of the build or dropped (C5).

**Explicitly not scheduled:** multi-user, class, and leaderboard views. They
depend on B4 *and* on keeping the answer key away from the client entirely, which
changes the `fetch-pdf` contract. `apps/solver/docs/future_work.md` §6.1 is right
that this should be decided before the schema hardens — but it is not blocking
anything today.
