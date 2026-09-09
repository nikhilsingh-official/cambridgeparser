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

> **Historical document.** This file preserves pre-merge decisions and can
> contradict the current repository. Use [`README.md`](../README.md) for the
> implemented system and [`docs/preproduction_issues.md`](preproduction_issues.md)
> for the current ranked backlog and release gates.

**What exists.** Two working applications and a pipeline that feeds one of them.

- **The pseudocode IDE** (`src/website/`) — landing, login, problem explorer,
  CodeMirror editor over a wasm build of the Rust parser, and model grading via
  `/api/grade` on Vercel. Deployed. Now on Supabase Auth and Postgres, sharing
  one project with Soluer (A1).
- **Soluer** (`apps/solver/`) — the MCQ paper solver. Highlight and eliminate
  options directly on the PDF, timed focus areas, full event recording, an
  end-of-exam summary that writes to Supabase. Runs locally only.
- **The pipeline** (`src/pipeline/`) — 118 segmented question papers, 119 mark
  schemes, 176 assembled records, all deterministic and tested (257 tests).

**Update (2026-08-20): the two apps are now one application.** `apps/solver` and
`src/website/frontend` are gone; everything under `src/` is a single Vue app with
one router, one shell, one sidebar and one session. The IDE is a page group
(Pseudocode IDE / Problems / Learn) beside the solver's (Paper Browser / Paper
Solver / Stats), and the landing page is the public front door. The Python
corpus pipeline is archived outside the repository; `api/` is the only Python
left and is self-contained. A1 and much of A3 are therefore done; A2 is now just
the deploy config, which `vercel.json` carries.

The paragraph below describes the state before that merge and is kept for the
history.

**What did not exist was a *site*.** The two apps now share a name, a
palette, a login design and — as of A1 — one Supabase project, so an account is
the same account in both. What they still lack is a shared deployment and any
routing between them, and none of the new SQL has been run against a real
database. Part A is that gap. Parts B and C are each app's own backlog.

Ordering is at the end (Part E). Read that first if you want to know what to do next.

---

## Part A — What blocks a unified cambridgeparser.com

### A1. One identity — **done in code, unverified against a database**

Both apps now run on one Supabase project. The IDE's Firebase Auth and Realtime
Database are gone: `services/supabase.js` replaces `services/firebase.js`,
`auth.js` keeps its exported names but calls `supabase.auth`, and the RTDB
subtree at `users/$uid/` became two tables.

| Was | Is | Client wired? |
|---|---|---|
| Firebase Auth | Supabase Auth, PKCE flow (implicit-flow tokens land in the fragment, which collides with hash routing) | **yes** |
| RTDB `users/$uid/profile` | `ide_profiles` | **no — nothing writes it** |
| RTDB `users/$uid/progress/$recordId` | `ide_progress`, with the best-score / never-un-solve rule moved from a client `runTransaction` into `record_ide_attempt()`; plus `ide_attempts`, the append-only log | **yes** — written by `api/_progress.py`, read by `lib/ide/useIdeProgress.ts` |
| RTDB `users/$uid/stats` | `v_ide_stats`, a view — counters that cannot drift from the rows they count; `v_ide_daily` beside it | **yes** — `lib/supabase/queries/ide.ts` |
| RTDB `gradingQuotas/$uid` + rule expressions | `grading_quotas` + `consume_grading_quota()`, `security definer`, no client-writable policy | **yes** — `api/_quota.py` |
| Firebase ID token verified via `accounts:lookup` | Supabase access token resolved via `/auth/v1/user` | **yes** — `lib/ide/grading.js` |
| `firebase.json`, `database.rules.json`, `.firebaserc` | deleted | — |

**Correction (2026-08-20).** An earlier version of this table read as though the
whole migration was done in code. It is not. The *schema* landed and the auth
and quota paths are live, but **the IDE persists nothing**: `IdeView.vue` saves
the editor buffer to `localStorage` and stops. `grep -rn record_ide_attempt src/`
returns nothing. So `ide_profiles` and `ide_progress` are empty tables with
policies on them, and everything downstream of them — `v_ide_stats`, A4, any
cross-app stat — is blocked on a writer that was never built, not on the
schema.

**Resolved (2026-08-23), except `ide_profiles`.** The writer exists, and it is
**on the server, not in the browser**: `api/_progress.py` calls
`record_ide_attempt()` from the same Vercel function that graded the answer,
with the caller's own token and the public anon key — so it holds no secret,
and the score is written by the code that computed it rather than by a client
that could invent one. That is the B4 property, obtained for the IDE up front
instead of retrofitted.

`ide_attempts` (migration `00000000000006`) landed **before** the writer, on
purpose: an upsert-only history is unrecoverable, so the log had to exist
before the first submission was recorded, not after. It is append-only at both
gates — select+insert policies with no update or delete policy, and
select+insert grants — so a past submission cannot be revised or erased through
the API. Covered by `tests/test_ide_attempts.sql`, and the RPC was exercised
end-to-end through PostgREST against the local stack.

`ide_profiles` is still written by nothing. It holds email and display name,
both already on `auth.users`, so it is the one row of this migration with no
consumer waiting on it.

Two properties were deliberately preserved. Vercel still holds **no admin
credential** — the anon key and the caller's own token are the whole credential
set. And `authReady` still resolves without waiting on the profile write, so a
hard refresh cannot stall behind a database round trip.

**Verified against a real database.** Both migrations were applied to a local
stack, and the flow was exercised end to end: sign-up through GoTrue, profile
upsert, `record_ide_attempt`, `v_ide_stats`, `consume_grading_quota`, and
`handle_grade` rejecting anonymous and forged tokens and returning 429 with a
retry once the burst window filled. The browser flow was driven too — protected
routes bounce to `/login`, registration lands in the app, and the session
survives a hard reload. `tests/test_grading_quota.sql` passes.

Running it found three defects that reading it had not:

1. **No table privileges for `authenticated`** on *any* table in either
   migration. This project's default privileges grant only
   REFERENCES/TRIGGER/TRUNCATE, so every statement failed with "permission
   denied for table" before a policy was ever consulted. RLS decides which rows
   a caller may touch; it does not grant the right to touch the table. This hit
   the **solver's schema too** — `exam_attempts` had no INSERT, so the entire
   end-of-exam write path would have failed the first time anyone finished a
   paper.
2. **`v_ide_stats` bypassed RLS.** A view runs with its owner's privileges
   unless created `with (security_invoker = true)`, so it read `ide_progress`
   as `postgres` and would have shown every user's counters to everyone. The
   solver's seven views had the same gap; they have no RLS to bypass *yet*,
   which is precisely why it would have gone unnoticed until B2 landed and
   silently failed to cover them.
3. `tests/test_grading_quota.sql` aged its windows with a direct `UPDATE` while
   acting as `authenticated` — which correctly has no such privilege. A bug in
   the test, but it proved the grant was right.

**What is still not done:**

- **Google OAuth needs configuring** in the Supabase dashboard. The client code
  is wired; the provider is not enabled, so that button fails until it is.
- The migrations have run against a *local* stack only, never a hosted project.
- **`pseudocode_attempts` was not designed.** Per `future_work.md` §6.2 it
  should be a *sibling* of `exam_attempts`, not a reuse — marking-point-level
  results do not fit a per-question MCQ row. `ide_progress` records the outcome
  of a submission but keeps no per-marking-point history.
- Old Firebase accounts were **not migrated** — a deliberate choice; there was
  nothing worth keeping. Anyone who had an account signs up again.

### A4. The stats page covers Soluer only — **done (2026-08-23)**

The page read `exam_attempts` and friends only, so a user's pseudocode work was
invisible beside their MCQ work and "accuracy" there silently meant "MCQ
accuracy".

Both halves are now built. The prerequisite — an append-only `ide_attempts` log,
the sibling of `attempt_events` — is migration `00000000000006`; see A1. On top
of it:

- `lib/supabase/queries/ide.ts`, the first consumers `v_ide_stats` has ever had.
- `model.ts` §I (`readIde`), so the IDE's figures are computed in the same file
  as every other claim this app makes about a student.
- `Ide-Overall.vue`, its own section on the stats page — **not** extra tiles on
  Progress. An MCQ question is right or wrong against one key and carries a
  20–25% chance floor; a pseudocode answer is marked against a rubric, can be
  half right, and has no chance floor. Averaging them produces a number that
  means nothing, and one shared axis invites the reader to average them anyway.
- Solved/attempted badges in the problem explorer, which is where the answer is
  actually useful — while choosing what to work on next.

Two things the section deliberately withholds rather than guesses. The
first-try rate is null when the attempt log came back truncated, because the cap
reads oldest-first and would report a biased sample as fact; and a student with
no submissions gets no section at all rather than a row of zeros.

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

### B1. The schema — **done, executed, verified**

~~25 kB of DDL that has never run against a database.~~ Both migrations, plus
`00000000000002_answer_changes.sql`, now apply cleanly to a local stack and are
exercised by the seed and by the stats page. The three generated-column
assumptions held; the `paper_id` CHECK regex holds for the whole catalogue. The
defects running it found are listed under A1. What follows is kept for the
method, not because it is outstanding.

```bash
npm run supabase:start
npm run supabase:reset    # applies both migrations and the 196-subject seed
```

Expect to fix DDL errors. Check in this order:

1. The five **generated columns** on `exam_attempts` — they assume `split_part`,
   `left`, `right`, `substr` and `::smallint` are all `IMMUTABLE`. Believed
   correct, unproven. Fall back to a `before insert` trigger if Postgres refuses.
2. The `paper_id` `CHECK` regex against your real paper set.
3. `drop table if exists attempts;` runs **last** — confirm it holds nothing.

### B2. RLS — the production gate

**Done 2026-08-20** — `00000000000003_solver_rls.sql`. All 14 public tables now
have RLS on; `tests/test_solver_rls.sql` proves isolation rather than asserting
it (owner sees 47 attempts / 1880 question rows / 1880 metrics, a second
authenticated user sees **0** through every table and every view, cannot insert
a row owned by someone else, cannot attach an event to someone else's attempt,
can still read the 196 subjects, and cannot rewrite the answer key).

Three things worth knowing about how it was written: policies use
`(select auth.uid())` rather than a bare call, so it is an InitPlan evaluated
once per statement instead of once per row — on `attempt_events` that is 1 call
instead of 1250. The derived tables (`question_attempts`, `attempt_events`,
`question_metrics`) have no `user_id` and reach ownership by EXISTS through
their parent attempt, rather than denormalising a column that could drift. And
the grants were narrowed to match the policies: `paper_answers` was UPDATE-able
by any authenticated client, which meant one user could rewrite the key and
change everybody's marks.

Still open here: `paper_answers` remains *readable* by any signed-in user
because the client marks the paper. No policy can fix that — it is B4.

The state this replaced, for the record:

| Tables | `relrowsecurity` | Policies |
|---|---|---|
| `ide_profiles`, `ide_progress`, `grading_quotas` | **on** | 3 / 3 / 1 |
| `ide_attempts` (added 2026-08-23) | **on** | 2 — select and insert only, by design |
| `exam_attempts`, `question_attempts`, `attempt_events`, `question_metrics`, `goals`, `profiles`, `paper_answer_keys`, `paper_answers`, `subjects`, `topics`, `metrics_versions` | **off** | none |

So the half of the app that stores nothing is locked down, and the half holding
every student's attempt history is open to any authenticated caller. Deliberate —
local emulators only, so far. Supabase default-denies, so
**nothing works in production without it**. Policies are already drafted in
`apps/solver/docs/database_design.md` §3.5.

Every query in `src/lib/supabase/queries/` takes an explicit `userId` and filters
on it. That predicate is currently the *only* thing scoping data to the right
user. Keep it even after RLS lands — defence in depth, and it makes the queries
readable.

One decision to make there: `paper_answers` must be client-readable today, which
means a determined user can read the answer key before answering.

### B3. The stats page — **built and verified against real data**

The read layer built in `aec4e13` finally has a consumer: `lib/stats/useStats.ts`.
The page reads seven views in parallel, the filters write straight into the query
filter, and every placeholder is gone — no Lorem ipsum, no `['Wade Cooper', ...]`,
no `testStats` array of `Math.random()` values.

Charts are ECharts, registered piecemeal in `lib/charts/echarts.ts` and split into
their own bundle chunk (StatsPage is 33 kB; ECharts caches separately at 658 kB).
Colours are validated palettes in `themes.scss` - one set per theme surface,
checked with the dataviz validator rather than by eye, in fixed order so a subject
keeps its colour across a re-filter.

`supabase/archived-seeds/02_dev_sample_data.sql` generates ~5 months of
plausible history for `dev@local.test` / `devpassword123` so the page is worth
looking at locally. It is now opt-in, refuses to run where non-dev accounts
exist, and is deterministic.

Four defects surfaced only by rendering it with real data:

1. **PostgREST truncated silently at `max_rows = 1000`.** `v_question_flags` is
   one row per question, so the focus section computed every number from 1000 of
   1840 rows - no error, no warning. `fetchQuestionFlags` now paginates.
2. **`StatsCard` derived its heading with `let` from destructured props**, so the
   value was captured once at setup. Invisible against a fixed test array;
   against live data `v-for` reused instances and cards showed one card's
   heading over another's value. Now `computed`, and keyed by category.
3. **The heatmap's `visualMap` defaulted to the wrong dimension.** Rows are
   `[week, weekday, minutes, date]` and visualMap maps the *last* dimension, so
   colour came off the date string and all 161 cells rendered in the darkest
   step - a populated calendar that looked empty.
4. **The accuracy chart invented plateaus.** A shared category axis of all dates
   plus `connectNulls` drew flat runs between each subject's sparse attempts,
   asserting steady accuracy across days holding no measurement. Now a time axis
   with each series carrying only its own points.

**Section recommendations.** Each of the three sections carries a one-line
reading above its charts, from `lib/stats/recommendations.ts`. These are RULES,
not a language model: a banner sits beside the chart it describes, so anything
that can contradict the numbers destroys trust in the page, and rules cannot -
they are computed from the same values. They are also deterministic (a changed
banner means changed behaviour, not a changed sample), auditable, and free.
Every rule returns a number it used.

The thresholds they read (0.7/0.4 confidence, 0.4x median for guesses) were
picked rather than measured, and the recommendations inherit that - which is an
argument for rules, since the number is visible and tunable.

A model would earn its place synthesising ACROSS sections into a study plan,
quoting figures it was handed rather than inventing them. That is a separate
feature from a per-section banner.

**Still open:** the IDE contributes nothing to this page yet - see A4.

### B4. Scores are still forgeable

`cacheAnswerKey.ts` writes the answer key **from the browser**, so a score is
only as trustworthy as the client that reported it. The `fetch-pdf` edge function
already parses the key server-side — it should write it directly and the client
function should be deleted.

This is the last step to unforgeable scores and a **hard prerequisite for any
shared, class, or leaderboard view**. Decide it before the schema hardens: it
changes the `fetch-pdf` contract.

### B0. The Dashboard is entirely fake — **the biggest remaining mock**

Not previously tracked, and it should have been: `/dashboard` is where every
sign-in lands. It performs **zero reads**. There is no `supabase` import, no
`useStats`, no fetch of any kind in `src/components_dashboard/`.

| Tile | Shows | Source |
|---|---|---|
| streak | `10 days`, `longest: 21 days` | literal, `QuickView.vue` |
| papers | `352` | literal |
| time | `12h 17m` | literal |
| accuracy | `157/170` | literal |
| StatsPrev panels | `16`, `12`, `5`, `3` | literal |

Every number is already computed and verified on the stats page — `useStats()`
returns totals, streaks and subject stats, and `computeStreaks()` exists. This is
a wiring job, not a data job. (`StatsPrev.vue` also spells it `Acccuracy`.)

`QuickView.vue` has no `<script>` block at all.

### B5. Unbuilt UI work

**Done 2026-08-20 — the Paper Browser is operational.** It was a mock: a
hardcoded array of 32 subject cards with invented paper codes, filters offering
`['Wade Cooper', ...]` / `['Cat','Dog','Rabbit']` bound to refs nothing read, a
literal `"3 days ago"` on every card, a `"Recommended"` tag on every card, and
**no click handler anywhere in the grid**. The only route into the solver was a
sidebar link hardcoded to `/solver/0455_w22_12`, so every student sat the same
Economics paper.

Now:

- `src/constants/paperCatalogue.ts` defines the papers that can be offered.
  There is no catalogue table — `fetch-pdf` resolves any schema on demand — so
  the grid is *generated* from the naming convention. It is restricted to
  multiple-choice papers because the solver's option parser and the mark-scheme
  reader both assume MCQs; 19 papers across 14 syllabuses (IGCSE sciences and
  Economics, four A Level, four O Level).
- All five filters work and compose: subject, year, season, variant, and
  progress (not attempted / in progress / completed), the last of which is not a
  catalogue property and is applied after the attempt join.
- `fetchPaperStates()` joins `v_attempt_summary` in, one row per paper. Cards
  carry the real last-attempt time, the real score and the completed/unfinished
  badge; "Recommended" fires on a stated rule (≥2 completed papers in that
  subject, averaging under 60%) and says so on hover.
- Cards navigate to `/solver/<schema>` and are keyboard-reachable. **Paper
  Solver was removed from the sidebar** — the page is about a specific paper and
  has no meaning without one.
- `MCQNav.setup()` ran unawaited and uncaught, so a paper the upstream mirror
  does not have left the loading screen cycling "Preparing the PDF..." forever.
  It now says so and offers the way back. This matters more than it did: the
  browser can offer any series/variant combination, and not all were sat.

Still open on the browser:

- The catalogue asserts which series and variants exist. It is right for the
  common cases and the Feb/March quirk (variant 2 only), but nothing verifies a
  combination against the mirror before showing it — a student can still pick a
  card that 404s. A HEAD-request probe, or caching what `fetch-pdf` learns,
  would close it.
- Non-MCQ subjects are simply absent. Extending the solver to structured papers
  is a much larger piece of work; extending the *catalogue* once it can is one
  array.

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
| ~~Answer-change quality~~ | **built** | `v_answer_changes` / `v_answer_change_summary` classify every consecutive pair of chosen options against the key. The Focus section shows the three outcomes and the net marks changing won or cost |
| Elimination precision | not built | `eliminated_mask` × `correct_option` — how often a ruled-out option really was wrong, and how often the *correct* one got eliminated |
| Pacing / fatigue | not built | `attempt_events` gives true answering order, which `question_number` cannot |
| Topic mastery | **done** | 734 topics and 57,145 question tags seeded from `structure.json` + `question_topics.json` by `scripts/buildTopics.ts`; `v_topic_mastery` reads `question_topics`, rendered by the stats page’s Topics section. Covers the 14 multiple-choice syllabuses only |
| Exam readiness / predicted grade | **done** | Component-level grade estimate with an 80% interval (`model.ts` §F), against real Cambridge thresholds — 406 published documents scraped and averaged by `scripts/gt/build.py` |

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
| **Leaked password** | High | A Supabase account password was hardcoded in `Login.vue` at commit `1857cf2` and removed by `fa220df`. The literal value is deliberately not repeated here. It was scrubbed from this repository's history (see below), but the **same password is committed and pushed** in another project — so it must be treated as public: **rotate it**, and rotate anything that reuses it |
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
3. ~~**B3** — install ECharts and wire `components_stats/`~~ — **done**. Next on
   that page is **A4**: put the IDE's work on it, which needs `ide_attempts`
   first.

**2 — Make the corpus gradeable.** Independent of the above; can run in parallel.

4. **C2** — run the 15-case evaluation set. The cases are already written; this is
   the cheapest way to learn whether the grading is any good.
5. **C1** — the 2015–2016 mark-scheme layout. The largest single content gap, and
   it should recover some of the 19 discarded records too.
6. **C4** — make stored screenshot paths relocation-proof, or at least tested.
   Do it before the next corpus rebuild, not after.

**3 — Make it one site.** Only worth starting once Soluer is worth deploying.

7. **A1 follow-through** — the port is written but unverified. Run
   `supabase db reset`, then `tests/test_grading_quota.sql`, and enable Google
   OAuth in the dashboard. Cheap, and it is load-bearing for everything else.
8. **B4 → B2** — server-side answer key, then RLS on the solver's tables. The
   IDE's new tables already have RLS; the solver's do not. Together these are
   the gate to deploying Soluer publicly at all.
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
