<!-- ==========================================================================
     Documentation only. Companion to DATABASE_DESIGN.md: that file specifies
     the target, this one tracks what is still outstanding after the data-layer
     pass, and why each item was deferred rather than done.
     ========================================================================== -->

# SmartSolver — Outstanding Work

Status after the data-layer pass. **Done** items are in §1 for context; §2 onward
is the actual backlog, ordered by what blocks the most.

---

## 1. Done in this pass

| Defect | Fix | Where |
|---|---|---|
| D1 correctness never stored | `question_attempts.is_correct`, set by trigger from a cached key | `schema.sql`, `cacheAnswerKey.ts` |
| D9 correctness client-asserted | `set_question_correctness()` trigger; client no longer sends it | `schema.sql` |
| D2 `time_spent_ms` held seconds | `* 1000` at the write boundary | `pushToAttemptsTable.ts` |
| D3 `marked_*_count` coerced to 0/1 | real counts passed through | `pushToAttemptsTable.ts` |
| D4 flag buttons inert | wired to `handleButtonClick` → `addEventLog` | `ActiveQuestionButtons.vue`, `composable.ts` |
| D6 `paper_id` unstructured | string kept as ground truth; `subject_code`/`series`/`exam_year`/`paper_number`/`variant` **generated from it** | `schema.sql` |
| D7 no raw events, no metric versioning | `attempt_events`, `question_metrics`, `metrics_versions` | `schema.sql`, `pushEventLogs.ts` |
| D8 no attempt lifecycle | `status` + `startExamAttempt()` / `finishExamAttempt()` | `pushToExamTable.ts`, `MCQNav.vue` |
| D10 local time lost | `client_timezone` + `local_date` on the attempt | `schema.sql`, `pushToExamTable.ts` |
| D11 dead `attempts` table | dropped | `schema.sql` |
| D12 four options hardcoded | `paper_answers.option_count` | `schema.sql` |
| — subject code → name | 196 subjects scraped from Cambridge, deterministic parse | `supabase/seed_subjects.sql`, `src/constants/subjectCodes.ts` |
| — over/underconfidence, guessing, calibration | added as views (they need `is_correct`, which did not exist before) | `schema.sql` |

**Verified:** `npx vite build` passes; `vue-tsc` errors went 22 → 20.
**Not verified:** the SQL has never been executed — no `psql`, `docker` or
`supabase` CLI in this environment. The `paper_id` parsing logic was validated
separately against real corpus schema strings. **Run `supabase db reset` and
read the errors before trusting any of the DDL.**

---

## 1b. Bugs surfaced by the typing pass

Adding types to previously-`any` boundaries exposed two real defects. Both had
been invisible because nothing checked the shapes involved.

### ⚠️ 1b.1 The exam lifecycle is never invoked — **persistence is unreachable**
`startExam()` and `endExam()` are defined in `MCQNav.vue` and **called from
nowhere**. They are not in its template and not passed to any child:

- `LoadingScreen.vue:98` has its own "Start Exam" button wired to a local
  `startCountdown()`, and the component declares **no `defineEmits`** — so the
  parent is never told.
- `BottomBar.vue` has no End Exam control at all.

Consequence: in the dashboard prong, **no attempt has ever been written to
Supabase**, and the entire write path added in §1 is dead code until this is
connected. `vue-tsc` reports both functions as unused, which is what gave it away.

Not fixed here, because it needs a product decision rather than a type: where
does "End Exam" live, and should `LoadingScreen` emit `start` or should MCQNav
own the button? Wiring it is a ~10-line change once that is decided.

### 1b.2 Deselection events were never logged — **fixed**
`selectOption.ts` built its log key as `` `${nextState}_${optionState}` `` while
`logMap` is keyed by *(mode, previous state)*. Since `nextState` is `"neutral"`
whenever the student deselects, the key came out as `neutral_correct` /
`neutral_eliminated` — neither of which is in the map — and the old
`if (logString)` guard silently swallowed the miss.

So `deselectedCorrect` and `deselectedElim` **could never fire**, which also
skewed `eliminationReversalCount` in `enrichAnalytics`. The smartsolver original
used `highlightMode.value`; the dashboard prong regressed it. Restored, and the
key is now a template-literal type so the lookup is total and a missing entry is
a compile error rather than a dropped event.

---

## 2. Blocking — do before building the stats page

### 2.1 Apply and validate the schema
Nothing downstream is real until `schema.sql` has actually run. Expect to fix
DDL typos. Specific things to check first:

- the five **generated columns** on `exam_attempts`. They rely on `split_part`,
  `left`, `right`, `substr` and `::smallint` all being `IMMUTABLE`. That is
  believed correct but unexecuted. If Postgres rejects any of them, fall back to
  a `before insert` trigger that populates plain columns.
- the `paper_id` `CHECK` regex against your real paper set. It accepts
  `0625_s25_22` and `0580_s24_1` and rejects malformed input (validated), but
  only against the schema strings this repo happens to contain.
- `drop table if exists attempts;` runs **last** in the file — confirm you have
  nothing in it.

### 2.2 Seed the reference data
```bash
supabase db reset
psql "$DB_URL" -f supabase/seed_subjects.sql     # 196 subjects
```

### 2.3 The query layer does not exist
The app still performs **zero reads**. Every view in §Read layer of `schema.sql`
is unconsumed. Until `src/lib/supabase/queries/` exists, the stats page cannot
show anything real regardless of what is stored.

### 2.4 Replace the placeholder data in `components_stats/`
- `StatsPage.vue:10–17` — filters hardcoded to `['Wade Cooper','Arlene Mccoy',…]`,
  `['Apple','Banana','Cherry']`, `['Red','Green','Blue']`. Should be years /
  series / variants, sourced from `v_attempt_summary`.
- `StatsPage.vue:33` — Lorem ipsum subtitle.
- `CardStrip.vue:4` — `testStats` generated array.
- `StatsPage.vue:56` — `.pie-container` is an empty div.

### 2.5 Backfill `is_correct` for anything already stored
Rows written before the answer key was cached get `is_correct = null` by design.
`remark_attempt(uuid)` re-fires the trigger. There is no bulk equivalent yet —
add one, or loop over `exam_attempts`.

---

## 3. Correctness and trust

### 3.1 Move the answer-key write into the edge function
`cacheAnswerKey.ts` writes from the browser, so the key is currently only as
trustworthy as the client that sent it. The `fetch-pdf` edge function *already
parses the key server-side* — it should write it directly, and the client
function should be deleted. This is the last step to making scores unforgeable,
and it is a **prerequisite for any shared, class or leaderboard view**.

### 3.2 RLS
Deferred deliberately — local emulators for now. **Nothing works in production
without it**, since Supabase default-denies. Policies are already drafted in
`DATABASE_DESIGN.md` §3.5. Do not deploy without them; also decide there whether
`paper_answers` stays client-readable (it currently must be, which means a
determined user can read the key before answering).

### 3.3 Move `enrichAnalytics` server-side — *when* you first retune weights
Kept client-side for now, which is the smaller change. The cost lands the first
time you change a weight: recomputing all history becomes a client-side backfill
rather than one SQL statement. `attempt_events` now makes recomputation possible
at all; where it runs is a separate decision.

---

## 4. Metrics not yet implemented

Infrastructure exists for all of these; none has a consumer.

| Metric | State | Needs |
|---|---|---|
| Calibration curve | `v_calibration_curve` written | a chart, and `question_metrics` populated |
| Over/underconfidence | `v_question_flags` written | thresholds validated against real data (currently 0.7 / 0.4, picked not measured) |
| Guess detection | `v_question_flags` written | the same — `< 0.4 × median` and `exploration_depth <= 1` are guesses about guessing |
| **Answer-change quality** | **not built** | the highest-value unbuilt metric. Now possible: `attempt_events` records every transition type (`setCorrect`, `elimToCorrect`, `correctToElim`, …) with the option index, so right→wrong vs wrong→right is derivable. `optionSwitchCount` only ever counted switches, never whether they helped. |
| Elimination precision | not built | `eliminated_mask` × `correct_option` — how often a ruled-out option really was wrong, and how often the *correct* answer was eliminated |
| Pacing / fatigue | not built | `attempt_events` gives true answering order, which `question_number` cannot |
| Topic mastery | `v_topic_mastery` + `topics` + `paper_answers.topic_id` exist | **content** — fill in `src/constants/topicMap.ts`, then call `seedTopics()` and `applyPaperTopics()` |
| Exam readiness / predicted grade | not built | grade-threshold table per subject; thin layer over accuracy + topic mastery |

**On the three thresholds:** the guess and confidence cut-offs are placeholders
chosen for plausibility, not fitted to data. Once a few hundred questions exist,
check them — a "guess" rule that fires on 40% of questions is measuring reading
speed, not guessing.

---

## 5. Application-level (unchanged from `MERGE_NOTES.md` §6)

| Item | Note |
|---|---|
| `npm run build` still fails | 20 `vue-tsc` errors. 10 are unused imports; 5 are the missing `declare module '*.vue'` shim in `src/vite-env.d.ts` — that one fix clears 5. Use `npx vite build` meanwhile. |
| Hardcoded Supabase endpoint | `useAuth.ts` points at `http://127.0.0.1:54321`. Move to `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` before any deploy. |
| `profiles` never written | The table exists; nothing upserts it. Do it on first sign-in, and store the IANA timezone there so it survives a device change. |
| `createPDFObservers.ts` dead | No importers, and its `renderTracks` call has the wrong argument order. Wire it or delete it. |
| `fetch-pdf` has no CORS | No `OPTIONS` branch, no `Access-Control-Allow-*`. Fine on localhost; breaks the moment it is deployed cross-origin. |
| Single 1.4 MB JS chunk | Route-level `import()` or `manualChunks` for `pdfjs-dist` / `@supabase/supabase-js` / `lottie-web`. `paper.png` is another 1.75 MB. |
| Leaked test credentials | `smartsolver/call_fetch_pdf.sh` (original prong, not copied here) has a real email + plaintext password. Rotate it. |
| `Sidebar` imported unused in `App.vue` | Each page renders its own; the import is dead. |

---

## 6. Decisions still open

**6.1 Multi-user.** Everything built so far is single-user-correct. A class or
leaderboard view requires §3.1 *and* keeping the answer key away from the client
entirely, which changes the `fetch-pdf` contract. Decide before the schema
hardens, not after.

**6.2 The Cambridge IDE merge.** Paused, and `SMARTSOLVER_CAMBRIDGE_MERGE_PLAN.md`
is now partly stale — it predates the discovery that `dashboard/` was the real
main line, and it assumes Firebase for the IDE side, which you have since said
will move to Supabase. When you pick it up, the pseudocode attempts most likely
become a sibling of `exam_attempts` rather than a reuse of it — which is also
the answer to what the old dead `attempts` table was reaching for.

**6.3 Event retention.** Unbounded is fine at personal scale. If it stops being
fine: keep events for the newest N attempts per user and keep `question_attempts`
forever — facts are small, events are the bulky recomputation substrate.

**6.4 `metrics_version` bump policy.** Version 1 is seeded with the weights
currently in `enrichAnalytics.ts`. Nothing yet enforces that changing those
weights also inserts a version 2 — it is a convention, and conventions decay.
Worth a comment at the top of `enrichAnalytics.ts` at minimum.
