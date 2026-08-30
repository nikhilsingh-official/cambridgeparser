<!-- =========================================================================

     Code-review issue register for the unified cambridgeparser.com app.
     This records only work still open after the 2026-08-27 pre-production
     bugfix pass. It supersedes status claims in older roadmap documents where
     those documents describe the former split-app repository.
     ========================================================================= -->

# Pre-production unresolved issues

Reviewed against the local repository and local Supabase stack through 2026-08-30.
The public `cambridgeparser.com` deployment was deliberately excluded because it
still serves the old IDE. “Confirmed” means the current implementation contains
the defect or limitation. “Release risk” means the code path could not be
validated in its real hosted/provider environment and must not be represented as
passing.

## Triage scales

| Scale | Meaning |
|---|---|
| P0 | Resolve or explicitly remove the affected workflow before public launch |
| P1 | Resolve before general availability; a constrained beta needs a documented mitigation |
| P2 | Important follow-up; the current product can operate with a visible limitation |
| P3 | Polish, optional feature, or operational improvement |

Complexity is comparative, not a delivery promise: **S** is less than a day,
**M** is roughly 1–3 engineering days, **L** is roughly 3–7 days, and **XL**
needs an architectural decision, migration, broad corpus work, or multiple
iterations.

Every entry in the master table is **unresolved** unless its note explicitly
names an applied mitigation. Confirmed failures below include reproduction,
expected/actual behavior, likely cause, severity/complexity, and fix status.
Release risks are not reported as observed failures; their closing evidence is
listed instead.

## Master ranking by implementation complexity

This is the single complexity-ordered inventory. Items in the same complexity
band are ordered by severity and release priority.

| Complexity rank | ID | Type | Severity | Summary |
|---:|---|---|---|---|
| 1 · XL | CP-001 | Confirmed trust defect | Critical | Shared answer keys are exposed and first-writer-controlled |
| 2 · XL | CP-005 | Confirmed limitation | High if mobile is promised | Phone-width dashboard and solver layouts are not usable |
| 3 · XL/data | CP-018 | Model risk | Medium | Analytics thresholds are hand-picked rather than calibrated |
| 4 · L–XL | CP-006 | Product gap | High if resume is promised | In-progress papers cannot be saved, resumed, or restarted |
| 5 · L | CP-003 | Confirmed persistence defect | High | Attempt completion is non-transactional and has no retry |
| 6 · L | CP-004 | Confirmed stats defect | High | Page-level filters control only some stats panels |
| 7 · L | CP-008 | Confirmed lifecycle defect | Medium | Tab-close abandonment can leave stale in-progress attempts |
| 8 · L | CP-015 | Integration risk | Medium–High | Every uncached solver load depends on one paper mirror |
| 9 · L | CP-017 | Compatibility risk | Medium | Vendored PDF.js v3 is mixed with npm pdfjs-dist v5 |
| 10 · L | GAP-001 | Product gap | Medium | Overview rows cannot navigate to their PDF questions |
| 11 · L | GAP-002 | Product gap | Medium | Paper Generator is not implemented |
| 12 · M–L | CP-016 | Performance risk | Medium | PDFs are transported as inflated JSON number arrays |
| 13 · M–L | CP-020 | Standards defect | Medium | Substantial Python tools/tests exist outside the only permitted Python directory |
| 14 · M–L | GAP-003 | Product gap | Low–Medium | Calendar has no route or data model |
| 15 · M | CP-007 | Confirmed auth defect | High | Recovery links have no set-new-password workflow; UI entry is now hidden |
| 16 · M | CP-011 | Production risk | High | Hosted Supabase schema, policies, seed, and function are unverified |
| 17 · M | CP-012 | Production risk | High | Real deployed Google/OpenRouter grading is unverified |
| 18 · M | CP-013 | Production risk | High | Hosted OAuth/provider configuration is unverified |
| 19 · M | CP-019 | Build/performance risk | Low–Medium | Lottie uses eval and ECharts produces a large route dependency |
| 20 · M | GAP-004 | Product gap | Medium | Profile and Settings workflows are not implemented |
| 21 · M | GAP-005 | Product gap | Low | Active-question copy is not implemented |
| 22 · M | GAP-006 | Product gap | Medium | Some Learn topics have no linked practice |
| 23 · S–M | CP-009 | Confirmed integration defect | Low | The default PDF.js locale bundle is missing |
| 24 · S–M | GAP-007 | Product gap | Low | Shortcut help has no in-product overlay |
| 25 · S operational | CP-014 | Production risk | High until exercised | Preview deployment and deep-link behavior are unverified |

CP-002 (representative PDF parsing coverage) is resolved: the catalogue now
excludes 2016 and earlier, and all 819 checks across the 19-family golden corpus
pass. Ambiguous non-linear choices deliberately select through verified A–D
markers with enlarged label hitboxes instead of claiming unsafe formula/table
fragment association. CP-010 (contradictory historical roadmap status) was
also mitigated. Both are excluded from the unresolved ranking.

## High-severity, high-complexity decisions

These are the issues most likely to require owner attention rather than another
small wiring pass.

| Rank | ID | Issue | Severity | Complexity | Why it is hard |
|---:|---|---|---|---|---|
| 1 | CP-001 | Shared answer keys are exposed and first-writer-controlled | Critical | XL | Fixing it changes the trust boundary, RLS/grants, grading contract, existing cached data, and potentially key ingestion. |
| 2 | CP-003 | Completing an attempt is a non-transactional multi-request write with no retry | High | L | A durable solution needs an atomic RPC or resumable idempotent protocol, failure-state UI, and recovery tests. |
| 3 | CP-004 | Stats filters change only some panels | High | L | Several database views have already aggregated away year/series/variant, so the missing dimensions cannot be restored in Vue. |
| 4 | CP-005 | The dashboard and solver are not usable at phone widths | High if mobile is launch scope; otherwise Medium | XL | The fixed viewport rail and dense solver/PDF layout need product-level responsive behavior, not isolated media queries. |
| 5 | CP-006 | Save/resume/restart is absent for in-progress papers | High for long-paper workflows | L–XL | True resume needs durable incremental answers/events, reconciliation, expiry, and a defined attempt state machine. |

## Confirmed unresolved defects

### CP-001 — Shared answer-key trust boundary

- **Priority:** P0
- **Severity / complexity:** Critical / XL
- **Evidence:** [`fetch-pdf/index.ts`](../supabase/functions/fetch-pdf/index.ts)
  returns `answers` to the browser. [`cacheAnswerKey.ts`](../src/lib/supabase/cacheAnswerKey.ts)
  then writes them into shared `paper_answer_keys` and `paper_answers` rows.
  [`00000000000003_solver_rls.sql`](../supabase/migrations/00000000000003_solver_rls.sql)
  deliberately allows every authenticated user to read and insert those rows.
- **Actual behavior:** any signed-in client can inspect a key before answering.
  For a paper not cached yet, any signed-in client can also insert the first
  shared key; `ON CONFLICT DO NOTHING` makes that untrusted first value
  immutable to later clients. A poisoned key therefore affects every later
  attempt on that paper.
- **Expected behavior:** only trusted, verified answer data decides correctness;
  a candidate must not be able to create or read the grading key through the
  ordinary client API.
- **Likely fix:** decide on a trusted ingestion architecture, pre-populate or
  server-verify keys, revoke client insert/read privileges, grade behind a
  narrow server/RPC boundary, and re-verify or replace existing cached keys.
  Do not paper over this with broader admin credentials in the browser or the
  Python grading API.
- **Short-term mitigation:** do not enable shared/class/leaderboard claims, and
  restrict the solver to a server-verified allow-list if one can be produced.
- **Steps to reproduce:** sign in, inspect the `fetch-pdf` response, then use the
  public client credentials to insert a new `paper_answer_keys`/`paper_answers`
  key for an uncached valid paper ID. A second insert cannot correct it.
- **Likely root cause:** answer extraction moved server-side, but persistence and
  marking retained the original client trust model.
- **Fixed:** No.

### CP-003 — Attempt completion can persist only part of a result

- **Priority:** P0
- **Severity / complexity:** High / L
- **Evidence:** [`endExam()` in MCQNav.vue](../src/components_navigator/MCQNav.vue)
  sequentially caches the key, writes question attempts, writes metrics, writes
  event chunks, and only then changes the attempt status to `completed`.
  [`EndScreen.vue`](../src/components_navigator/EndScreen.vue) reports a save
  failure but exposes no retry. Review mode freezes further writes.
- **Actual behavior:** a network/database failure between requests can leave an
  `in_progress` attempt with only some child rows. The candidate sees a local
  score and “attempt not saved”, but cannot retry without re-sitting the paper.
- **Expected behavior:** finishing is atomic, or the same finish payload can be
  safely resumed until all rows and final status are durable.
- **Likely fix:** one transactional database RPC is preferred. If payload size
  requires chunks, persist a completion id/state machine, make every chunk
  idempotent, expose retry, and test failures after every stage.
- **Steps to reproduce:** finish a paper while forcing one request after
  `pushToAttemptsTable()` to fail, then inspect the attempt and try to retry from
  the result screen.
- **Likely root cause:** persistence was added as independent client writers
  without a transaction coordinator or durable completion state.
- **Fixed:** No.

### CP-004 — The global stats filter has mixed scope

- **Priority:** P1
- **Severity / complexity:** High / L
- **Evidence:** [`useStats.ts`](../src/lib/stats/useStats.ts) applies the complete
  filter to attempt summaries and question flags, but deliberately reads daily,
  hour, subject, calibration, answer-change, and IDE aggregates unfiltered.
  Topic rows can honor subject only; their views have already pooled year,
  series, and variant.
- **Actual behavior:** selecting subject/year/series updates some totals and
  charts while other panels keep all-time/all-paper data without a persistent
  scope label. A single page-level filter therefore makes internally
  inconsistent claims.
- **Expected behavior:** every visible panel honors the selected scope, or is
  clearly separated and labelled as global before the user interacts.
- **Likely fix:** choose one contract. Either add filter dimensions to the
  underlying views/queries, or split global panels into a visibly unfiltered
  section and remove the implication that the page filter controls them.
- **Steps to reproduce:** open `/stats` with multiple subjects/years, select one
  year or series, and compare the filtered paper totals with the activity,
  subject, calibration, answer-change, topic, and IDE panels.
- **Likely root cause:** aggregate views discarded filter dimensions before the
  page-level filtering contract was introduced.
- **Fixed:** No. The separate rapid-filter response race was fixed in this pass.

### CP-007 — Password-reset links cannot complete a reset

- **Priority:** P0
- **Severity / complexity:** High / M
- **Evidence:** [`sendPasswordReset()`](../src/stores/useAuth.ts) redirects the
  recovery link to `/login`, but [`Login.vue`](../src/components_auth/Login.vue)
  has no recovery mode and never calls `supabase.auth.updateUser()` with a new
  password. The guest-only route redirects an authenticated recovery session to
  `/dashboard`.
- **Steps to reproduce:** generate a recovery email through the existing
  `sendPasswordReset()` store method (or a Supabase recovery test), open the
  delivered link, and attempt to set a new password.
- **Actual behavior:** there is no new-password form; the user is redirected into
  the app and the forgotten password remains unchanged.
- **Expected behavior:** a recovery session lands on a dedicated, validated
  password form, updates the password, handles expired links, and then signs in
  or returns to login.
- **Likely root cause:** the mail-dispatch half was implemented without a
  recovery-session route/state and `updateUser()` form.
- **Mitigation applied:** **Forgot password** is now hidden until the recovery
  route is complete.
- **Fixed:** No; the dead entry point is removed, but account recovery is absent.

### CP-008 — Tab-close abandonment is best-effort only

- **Priority:** P1
- **Severity / complexity:** Medium / L
- **Evidence:** [`handleBeforeUnload()`](../src/components_navigator/MCQNav.vue)
  starts an asynchronous Supabase update while the page is tearing down. Browsers
  are permitted to cancel it.
- **Actual behavior:** route changes normally mark attempts `abandoned`, but tab
  close, browser crash, network loss, or device sleep can leave permanent
  `in_progress` rows.
- **Expected behavior:** stale attempts converge to a known abandoned/expired
  state even when the browser cannot send its final request.
- **Likely fix:** add server-side stale-attempt expiry, optionally backed by a
  heartbeat/last-seen timestamp and an explicit resume policy.
- **Steps to reproduce:** start a paper, close the browser process or disable the
  network before closing the tab, then query the attempt after teardown.
- **Likely root cause:** correctness depends on an async request during a browser
  lifecycle phase that does not guarantee network completion.
- **Fixed:** No.

### CP-009 — Missing default PDF.js locale produces repeated warnings

- **Priority:** P2
- **Severity / complexity:** Low / S–M
- **Evidence:** local solver runs emitted repeated missing-localization warnings
  for page, loading, thumbnail, and editor labels. `public/web/locale` contains
  only `az`, `es-ES`, `gd`, and `trs`; no `en-US/viewer.properties` is committed
  even though [`locale.properties`](../public/web/locale/locale.properties)
  references the full locale set.
- **Actual behavior:** tested papers render, but one run produced hundreds of
  warnings and some PDF.js accessibility labels may fall back incorrectly.
- **Expected behavior:** the vendored viewer includes the matching default
  locale resources with no missing-key warnings.
- **Likely fix:** restore the locale file from the exact vendored PDF.js release,
  not a hand-written partial list.
- **Steps to reproduce:** load a solver paper and inspect the browser console for
  missing Fluent localization IDs.
- **Likely root cause:** only four locale directories were copied with the
  vendored viewer, while its locale manifest still references the full set.
- **Fixed:** No.

### CP-020 — Python exists outside the permitted application boundary

- **Priority:** P2
- **Severity / complexity:** Medium / M–L
- **Evidence:** root [`AGENTS.md`](../AGENTS.md) says “`api/` is the only
  Python.” The current worktree also contains `scripts/gt/*.py`,
  `scripts/qtype/qtype.py`, and `tests/test_progress_args.py`.
- **Actual behavior:** the repository cannot satisfy its own language/module
  boundary, and a clean commit of the current worktree would institutionalize
  the contradiction.
- **Expected behavior:** Python is self-contained under `api/`; offline pipeline
  code is archived outside this repository as the guideline requires.
- **Steps to reproduce:** run `find . -path ./api -prune -o -name '*.py' -print`
  from the repository root.
- **Likely root cause:** offline analysis tooling and a contract test were added
  without reconciling them with the post-merge repository invariant.
- **Likely fix:** decide ownership first, then move compatible API tests under
  `api/`, rewrite retained repository tooling in the supported stack, or archive
  the offline scripts outside the repository. Do not delete/move this untracked
  work without confirming it is safe.
- **Fixed:** No.

## Unverified production and integration risks

These are not claimed as observed failures. They remain release risks because
the local environment cannot prove them.

| Rank | ID | Risk | Severity | Complexity | Required evidence before closing |
|---:|---|---|---|---|---|
| 1 | CP-011 | Hosted Supabase migrations, grants, RLS, seed data, and `fetch-pdf` deployment have not been exercised as the production project | High | M operational | Fresh hosted deployment, SQL checks, two-user isolation test, and one persisted solver attempt |
| 2 | CP-012 | Google/OpenRouter grading has not been exercised through the deployed Vercel function with real provider credentials | High for IDE submissions | M operational | Valid, invalid, quota, timeout, provider-fallback, and persistence tests against preview deployment |
| 3 | CP-013 | Google, Azure, Twitter, email confirmation, and redirect allow-lists depend on hosted Supabase/provider configuration | High for the advertised auth methods | M operational | Test each enabled method from production and preview origins; hide providers that are not configured |
| 4 | CP-014 | The deployed site and history rewrites have not been smoke-tested because the current domain is the old product | High | S operational | Preview deployment tests for refresh/deep links, `/api/grade`, `/web/viewer.html`, assets, and all auth callbacks |
| 5 | CP-015 | The solver depends on a third-party paper mirror for every uncached QP/MS fetch | Medium–High | L | Availability monitoring, bounded size/time tests, cache behavior, user-facing outage state, and a fallback/storage policy |
| 6 | CP-016 | The edge function serializes a PDF as a JSON number array | Medium | M–L | Measure largest catalogue response against Supabase/browser memory and response limits; replace with binary/object storage if needed |
| 7 | CP-017 | Vendored PDF.js viewer v3 is driven with npm `pdfjs-dist` v5 utilities/types | Medium | L | Pin one compatible release or isolate versions completely; run the golden paper suite after upgrade |
| 8 | CP-018 | Analytics/recommendation thresholds are hand-picked rather than calibrated on user outcomes | Medium | XL/data | Collect labelled traces, validate calibration/false-positive rates, version any changed model, and backfill from raw events |
| 9 | CP-019 | The production build warns about `eval` inside `lottie-web`, and the ECharts chunk is about 658 kB minified | Low–Medium | M | Replace or isolate the decorative Lottie dependency, measure route startup on realistic devices, and further split/load charts only when needed |

One production-only deployment bug found during this review is **not** in the
open list: the global Vercel `X-Frame-Options: DENY` header would have blocked
the same-origin PDF viewer iframe. It has been changed to `SAMEORIGIN`; the
preview smoke test in CP-014 must verify the deployed behavior.

## Known product gaps, ranked by implementation complexity

These controls are now disabled or passive, so they no longer pretend to work.
They are not release regressions unless the launch scope promises them.

| Complexity rank | Gap | Severity if promised | Notes |
|---:|---|---|---|
| XL | Responsive phone solver/dashboard | High | CP-005; requires layout and interaction design, including the PDF viewer and side panels |
| L–XL | Mid-paper save/resume and restart | High | CP-006; restart alone is smaller, but honest resume is a persistence feature |
| L | Clickable Overview navigation | Medium | Rows show real state but do not yet scroll/focus the PDF question |
| L | Paper Generator | Medium | Disabled sidebar item; needs generation rules, validation, and a route/workflow |
| M–L | Calendar | Low–Medium | Disabled sidebar item; requires a scheduling data model if it is more than a local view |
| M | Profile and Settings | Medium | Disabled controls; profile data exists but no current settings workflow writes it |
| M | Copy active question | Low | Disabled because the parsed question text is not exposed through the active-question state |
| M | Practice for every Learn topic | Medium | Unsupported syllabus-extension records explicitly show “practice coming soon” |
| S–M | Shortcut-help overlay | Low | Shortcuts exist, but there is no in-product reference panel |

The WASM pseudocode parser validates supported syntax but does not execute
general programs. That is an intentional product boundary, not a defect, unless
the launch copy promises program output.

## Recommended resolution order

1. Choose and implement the CP-001 answer-key trust model.
2. Make CP-003 completion atomic/resumable and implement CP-007 password
   recovery; its broken UI entry is already hidden.
3. Resolve CP-004 by either changing the data grain or separating global stats.
4. Deploy a preview and close CP-011 through CP-014 with real hosted tests.
5. Decide whether mobile and resume are launch promises; if not, keep their
   current limitations explicit.
6. Address P2/P3 cleanup and product gaps after the integrity gates pass.

Until the P0 items are resolved or their workflows are removed from the release,
the recommendation from this review is **not ready for a public production push**.
