<!-- =========================================================================

     Code-review issue register for the unified cambridgeparser.com app.
     This records only work still open after the 2026-08-27 pre-production
     bugfix pass. It supersedes status claims in older roadmap documents where
     those documents describe the former split-app repository.
     ========================================================================= -->

# Pre-production unresolved issues

Reviewed against the local repository and local Supabase stack through 2026-09-07.
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
| 1 · XL/data | CP-018 | Model risk | Medium | Analytics thresholds are hand-picked rather than calibrated |
| 2 · L–XL | CP-006 | Product gap | High if resume is promised | In-progress papers cannot be saved, resumed, or restarted |
| 3 · L | CP-008 | Confirmed lifecycle defect | Medium | Tab-close abandonment can leave stale in-progress attempts |
| 4 · M–L | CP-020 | Standards defect | Medium | Offline Python tooling remains outside the supported application boundary |
| 5 · M | CP-022 | Confirmed dependency vulnerability | High | Both PDF.js copies are inside arbitrary-JavaScript advisory ranges |
| 6 · M | CP-011 | Production risk | High | Hosted Supabase schema, policies, seed, and functions are unverified |
| 7 · M | CP-012 | Production risk | High | Real deployed Edge grading is unverified |
| 8 · M | CP-013 | Production risk | High | Hosted OAuth/provider configuration is unverified |
| 9 · M | GAP-004 | Product gap | Medium | Profile and Settings workflows are not implemented |
| 10 · M | GAP-006 | Product gap | Medium | Some Learn topics have no linked practice |
| 11 · S–M | GAP-007 | Product gap | Low | Shortcut help has no in-product overlay |
| 12 · S operational | CP-014 | Production risk | High until exercised | Preview deployment and deep-link behavior are unverified |

CP-001 and CP-003 are resolved by migration 00000000000008: answer-key writes
are service-only, every legacy key is discarded, retained attempts are pending
until re-marked, and solver completion is one retry-safe transaction. Direct
browser mutation of completed solver/IDE history is also revoked. CP-002
(representative PDF parsing coverage) is resolved: the catalogue now
excludes 2016 and earlier, and all 819 checks across the 19-family golden corpus
pass. Ambiguous non-linear choices deliberately select through verified A–D
markers with enlarged label hitboxes instead of claiming unsafe formula/table
fragment association. CP-010 (contradictory historical roadmap status) was
also mitigated. Both are excluded from the unresolved ranking.

At the owner's direction on 2026-09-04, CP-009 (missing PDF.js locale), CP-015
(single paper mirror), and CP-017 (mixed PDF.js versions) are accepted and no
longer tracked as release issues. This is a scope decision, not a claim that the
underlying technical conditions changed.

The 2026-09-01 low-complexity pass also removed three failure amplifiers that
are not unresolved entries: topic-practice history is no longer silently cut at
1,000 rows (the local cap is 10,000 and the read is count-paginated), malformed
or rubric-inconsistent AI scores are rejected before persistence, and transient
Google 408/500/502/503/504 or network failures can fall back to OpenRouter after one
retry. Statistics reads now fail by progress/topics/focus/engagement/IDE group,
with a visible section-level error, rather than one rejected query clearing the
whole page. CP-004 is now resolved by narrowing the page contract to the one
dimension every solver section can represent: subject.

## High-severity, high-complexity decisions

These are the issues most likely to require owner attention rather than another
small wiring pass.

| Rank | ID | Issue | Severity | Complexity | Why it is hard |
|---:|---|---|---|---|---|
| 1 | CP-006 | Save/resume/restart is absent for in-progress papers | High for long-paper workflows | L–XL | Resume needs durable incremental state and reconciliation. |

## Resolved integrity defects

### CP-001 — Shared answer-key trust boundary

- **Corrected severity:** High persisted-data integrity; answer visibility and
  the fresh in-browser score were never affected by the cache.
- **Fix:** `fetch-pdf` now validates and installs the freshly parsed key through
  a service-only RPC. Authenticated key DML is revoked. Legacy keys are deleted,
  old correctness becomes pending, and a later verified fetch re-marks retained
  attempts for that paper.
- **Verification:** `test_trusted_writes.sql` proves browser insertion and RPC
  execution fail while the service role can install and re-mark a key.
- **Fixed:** Yes locally; hosted migration/function deployment remains CP-011.

### CP-003 — Attempt completion can persist only part of a result

- **Fix:** `finalize_exam_attempt` validates and writes questions, metrics,
  events, server-computed correctness, totals and status in one transaction.
  A unique completion UUID makes lost-response retries idempotent, and the end
  screen exposes Retry save. Direct child-table and completed-attempt DML is
  revoked from authenticated users.
- **Verification:** SQL tests cover atomic completion, idempotent replay, and
  attempted mutation/deletion of completed history.
- **Fixed:** Yes locally; hosted rollout remains CP-011/CP-014.

### CP-004 — Statistics panels had mixed filter scopes

- **Contract chosen:** the page exposes a subject filter for solver analytics;
  year, series, and variant controls were removed because existing topic views
  have already aggregated those dimensions away. IDE analytics are independent
  of paper subjects and are visibly labelled all-time.
- **Fix:** attempts are fetched once for the selected subjects and now drive
  progress, subject totals, daily activity, local-hour activity, and streaks.
  Focus flags, calibration, and raw answer changes use the same subject scope;
  topic mastery/practice is narrowed by subject before recommendations render.
- **Verification:** aggregation tests cover weighted subject totals, daily/hour
  activity, calibration, and answer-change summaries. The `/stats` browser test
  confirms the single filter and the scoped PostgREST requests.
- **Fixed:** Yes locally; preview verification remains part of CP-014.

The same pass moved IDE grading to Supabase and made its recorder service-only;
an authenticated caller can no longer invoke an RPC with an invented score.

### CP-005 — Unsupported phone layouts remained interactive

- **Product boundary chosen:** authenticated application pages require a
  viewport at least 768 CSS pixels wide. Public landing, sign-in, sign-up, and
  password-recovery screens remain available on narrow screens.
- **Fix:** narrow authenticated routes do not mount the sidebar or route
  component. They render a dedicated desktop-required screen with a working
  sign-out action, so an unusable solver cannot start invisibly underneath it.
- **Verification:** policy tests cover 767/768-pixel boundaries and public
  exceptions. A real authenticated browser session at 390 × 844 showed only
  the blocker; sign-out returned to the usable mobile login screen.
- **Fixed:** Yes for the stated desktop-only launch scope. Responsive solver
  and dashboard layouts remain future product work, not advertised behavior.

### CP-007 — Password recovery had no completion path

- **Fix:** sign-in now exposes a neutral account-recovery request form and
  sends links to a dedicated `/reset-password` route. The auth store captures
  the Supabase `PASSWORD_RECOVERY` event, rejects forged recovery URL intent,
  and permits `updateUser({ password })` only with both recovery intent and a
  live session. The form checks an eight-character minimum and confirmation,
  maps stable Auth error codes, removes callback material from browser history,
  signs out after success, and handles invalid/expired links without exposing
  account existence.
- **Verification:** pure tests cover callback errors and prove that forged URL
  recovery intent/credentials cannot grant reset authority, plus password rules.
  A real local GoTrue/Mailpit recovery email was
  requested and followed; mismatch was rejected, the password was changed,
  the recovery session was discarded, and a fresh login with the new password
  succeeded. Direct navigation without recovery authorization failed closed.
- **Fixed:** Yes locally. Hosted redirect allow-list, SMTP, and deployment
  verification remain operational work under CP-013 and CP-014.

### CP-021 — Explicit user-intent signals were inverted in persisted analytics

- **Fix:** separate increasing intent signals from the decreasing review-based
  confidence penalty. Star now increases difficulty; Save and review Flag now
  increase interest. Analytics use each toggle's final state, so turning it off
  clears the signal and repeated on/off cycles cannot inflate it. Button logging
  is synchronized to the active question and cannot create question zero.
- **Verification:** regression tests cover monotonicity, deselection, and an
  on/off/on cycle. A real solver run also confirmed that changing the active
  question enables the corresponding actions rather than retaining the previous
  question's state.
- **Historical caveat:** existing version-1 composites were not backfilled and
  remain unsuitable for cross-version comparison. These values are not exposed
  by the current Stats UI.
- **Fixed:** Yes for newly completed attempts.

The 2026-09-04 cleanup also resolved CP-016: `fetch-pdf` now carries binary PDF
data and JSON metadata in one multipart response. The largest golden PDF passed
byte-for-byte unit/client checks and a live local Edge invocation with all 40
answers. CP-019's Lottie `eval` path and duplicate wrapper dependency were
removed; ECharts registrations were pruned. The remaining 635 KiB route-only
ECharts chunk warning is a measurement-led optimization rather than a confirmed
release defect. Overview rows now navigate to the corresponding PDF question,
and active-question Copy uses the existing parsed segment. Paper Generator and
Calendar were removed from navigation instead of retained as disabled promises.

## Confirmed unresolved defects

### CP-022 — Installed PDF.js version has a high-severity advisory

- **Priority:** P0 before processing PDFs from an external source in production.
- **Severity / complexity:** High / M.
- **Evidence:** `npm audit` reports
  [`GHSA-hq66-cqwq-w95j`](https://github.com/advisories/GHSA-hq66-cqwq-w95j)
  against the installed direct dependency `pdfjs-dist@5.7.284`. The reported
  vulnerable range is `>=5.6.83 <6.2.108` and the advisory describes arbitrary
  JavaScript execution when opening a malicious PDF. Separately, the viewer
  actually served from `public/web/viewer.html` vendors PDF.js 3.2.146 in
  `public/build/pdf.js`; it is affected by
  [`GHSA-wgrm-67xf-hhpq`](https://github.com/advisories/GHSA-wgrm-67xf-hhpq)
  because `isEvalSupported` defaults to true. That older viewer also enables
  PDF scripting by default and the deployment has no Content Security Policy.
- **Steps to reproduce:** run `npm audit` in the repository root.
- **Actual behavior:** the production dependency audit exits non-zero with one
  high-severity vulnerability.
- **Expected behavior:** the PDF parsing stack has no known high-severity
  advisory applicable to its installed version.
- **Likely fix:** treat the imported library and vendored viewer as one upgrade:
  move both to one patched version, disable `isEvalSupported` and PDF scripting
  unless a verified workflow needs them, add a restrictive viewer CSP, then
  rerun the entire 19-family golden corpus, multipart Edge path, solver browser
  workflow, and build.
- **Fixed:** No. It was discovered by the final audit and is deliberately not
  hidden by raising audit thresholds or applying an unverified major upgrade.

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

### CP-020 — Python exists outside the permitted application boundary

- **Priority:** P2
- **Severity / complexity:** Medium / M–L
- **Evidence:** root [`AGENTS.md`](../AGENTS.md) says “`api/` is the only
  Python.” The current worktree also contains `scripts/gt/*.py` and
  `scripts/qtype/qtype.py`.
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
| 2 | CP-012 | Google/OpenRouter grading has not been exercised through the deployed Supabase Edge Function with real provider credentials | High for IDE submissions | M operational | Valid, invalid, quota, timeout, provider-fallback, and trusted persistence tests against preview deployment |
| 3 | CP-013 | Google, Azure, GitHub, email confirmation/recovery, SMTP, and redirect allow-lists depend on hosted Supabase/provider configuration | High for the advertised auth methods | M operational | Add the exact recovery redirect, configure SMTP, test email flows and each enabled OAuth method from production/preview origins, and hide providers that are not configured |
| 4 | CP-014 | The deployed site and history rewrites have not been smoke-tested because the current domain is the old product | High | S operational | Preview tests for refresh/deep links, both Edge Functions, `/web/viewer.html`, assets, and all auth callbacks |
| 5 | CP-018 | Analytics/recommendation thresholds are hand-picked rather than calibrated on user outcomes | Medium | XL/data | Separate product policy from estimators, collect labelled traces, validate false-positive/ranking quality, version changes, and backfill derived metrics |

One production-only deployment bug found during this review is **not** in the
open list: the global Vercel `X-Frame-Options: DENY` header would have blocked
the same-origin PDF viewer iframe. It has been changed to `SAMEORIGIN`; the
preview smoke test in CP-014 must verify the deployed behavior.

## Known product gaps, ranked by implementation complexity

These controls are now disabled or passive, so they no longer pretend to work.
They are not release regressions unless the launch scope promises them.

| Complexity rank | Gap | Severity if promised | Notes |
|---:|---|---|---|
| L–XL | Mid-paper save/resume and restart | High | CP-006; restart alone is smaller, but honest resume is a persistence feature |
| M | Profile and Settings | Medium | Disabled controls; profile data exists but no current settings workflow writes it |
| M | Practice for every Learn topic | Medium | Unsupported syllabus-extension records explicitly show “practice coming soon” |
| S–M | Shortcut-help overlay | Low | Shortcuts exist, but there is no in-product reference panel |

The WASM pseudocode parser validates supported syntax but does not execute
general programs. That is an intentional product boundary, not a defect, unless
the launch copy promises program output.

The authenticated application is likewise an explicit desktop-only product at
launch: widths below 768 CSS pixels receive a blocker instead of an interactive
dashboard, solver, stats, or IDE layout. Building genuinely responsive versions
of those screens remains future product work, but is no longer an ambiguous or
silently broken launch path.

## Recommended resolution order

1. Resolve CP-022 before accepting externally sourced PDFs in production.
2. Deploy a preview and close CP-011 through CP-014 with real hosted tests,
   including the new exact recovery redirect and SMTP-backed reset flow.
3. Keep save/resume outside launch promises unless CP-006 is implemented.
4. Address P2/P3 cleanup and product gaps after the integrity gates pass.

Until the hosted Supabase, provider, OAuth and preview gates are exercised, the
recommendation remains **not ready for a public production push**.
