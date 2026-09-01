<!--
It documents the repository as verified during the August–September 2026 release review.
-->

# CambridgeParser

[cambridgeparser.com](https://cambridgeparser.com) is one Vue application for
Cambridge International students. It combines a timed multiple-choice paper
solver with a Cambridge pseudocode IDE, a searchable question corpus, learning
material, and progress analytics. Both areas use the same routes, account,
Supabase project, navigation shell, and theme system.

The solver and IDE were separate applications in the past. They must not be
deployed, routed, or authenticated as separate sites.

## Features

- Email/password sign-up, sign-in, session restoration, and
  Google, Microsoft/Azure, or Twitter OAuth entry points.
- A curated browser of solvable IGCSE, O Level, and AS/A Level MCQ papers with
  subject, year, series, variant, and progress filters.
- A timed PDF paper runner with answer selection, option elimination, flags,
  an overview, finish confirmation, result review, and persisted attempts.
- Dashboard and statistics views backed by real attempt, topic, focus-area,
  recommendation, and IDE-submission data.
- A searchable Cambridge 9618 pseudocode question corpus with tag filtering,
  direct question links, editor source persistence, formatting, and a WASM
  parser that reports syntax diagnostics.
- Fill-in-the-blank and free-form IDE questions with authenticated AI grading,
  trusted server-side mark schemes, daily quota enforcement, and progress
  recording.
- A public landing page, an authenticated learning page, and light, dark, and
  monochrome themes.

## Architecture

| Layer | Implementation |
|---|---|
| Web client | Vue 3, TypeScript, Vite, Pinia, Vue Router, CodeMirror, ECharts, and PDF.js under `src/` |
| Authentication | One Supabase client and session in `src/stores/useAuth.ts`; route protection in `src/router/router.ts` |
| Application data | Supabase Postgres, Row Level Security, RPCs, ordered migrations, and development seeds under `supabase/` |
| MCQ paper retrieval | Authenticated `fetch-pdf` Supabase Edge Function; fetches the PDFs, parses and atomically installs a verified answer key, then returns the paper |
| IDE grading | Authenticated Supabase `grade` Edge Function; Google AI Studio is primary and OpenRouter is the fallback |
| IDE corpus/parser | Committed records and images in `public/resources`, plus a committed WASM parser built from `pseudocode-parser/` |
| Hosting | Vercel serves the Vite `dist/` client and rewrites history-mode deep links; Supabase hosts both server functions |

The browser never supplies an authoritative mark or user ID. The grading
function derives identity from the caller's JWT and records the model result
through a service-only RPC. `fetch-pdf` installs answer keys through a separate
service-only RPC, while solver completion crosses one authenticated,
transactional, idempotent RPC boundary. Completed histories are read-only.

## Routes and main workflows

| Route | Access | Purpose |
|---|---|---|
| `/` | Public; signed-in users go to `/dashboard` | Product landing page |
| `/login` | Signed-out users | Email/OAuth sign-in and account creation |
| `/dashboard` | Authenticated | Summary and entry points into solver and IDE work |
| `/browser` | Authenticated | Find an MCQ paper and open its solver |
| `/solver/:schema` | Authenticated, full screen | Sit, finish, and review one paper such as `0610_s26_11` |
| `/stats` | Authenticated | Filtered solver and IDE progress analytics |
| `/problems` | Authenticated | Search and filter the pseudocode corpus |
| `/ide` and `/ide/:id` | Authenticated | Parse and submit free-form or fill-blank answers |
| `/learn` | Authenticated | Pseudocode learning topics and links to related practice |

A normal solver flow is: sign in, choose a paper in `/browser`, start the
paper, answer or flag questions, finish it, review the locked result, and view
the persisted outcome in the dashboard/browser/stats views. A normal IDE flow
is: choose a problem, write or fill an answer, run the local parser where
applicable, invoke the `grade` Edge Function, inspect the mark scheme and feedback, and
see the recorded attempt in progress views.

## Repository structure

| Path | Contents |
|---|---|
| `src/main.ts`, `src/App.vue` | Application bootstrap and shared shell |
| `src/router/router.ts` | The single history-mode router and auth guard |
| `src/stores/useAuth.ts` | The single Supabase browser client and reactive session |
| `src/components_dashboard/` | Dashboard |
| `src/components_browser/` | Paper catalogue, filters, and paper cards |
| `src/components_navigator/` | Full-screen MCQ paper runner |
| `src/components_stats/` | Statistics and recommendations |
| `src/components_ide/`, `src/views/` | IDE, problems, learn, login, and landing views |
| `src/lib/` | PDF annotation/rendering, statistics, IDE services, domain logic, and Supabase reads/writes |
| `src/styles/themes.scss` | The only source of cross-theme design tokens |
| `src/styles/ide.css` | IDE component rules; it does not own design tokens |
| `scripts/gt/`, `scripts/qtype/` | Current untracked/offline Python analysis tooling; this violates the repository's `api/`-only Python rule and is tracked as CP-020 |
| `supabase/migrations/` | Database schema, RLS, topic practice, IDE attempts, and grading-quota functions, applied in filename order |
| `supabase/seeds/` | Subjects, topics, and local sample data |
| `supabase/functions/fetch-pdf/` | MCQ question-paper proxy, mark-scheme parser, and trusted key installer |
| `supabase/functions/grade/` | Authenticated IDE grading, provider routing, quota use, and trusted history recording |
| `public/resources/` | Committed pseudocode records, layouts, and question images |
| `public/wasm/` | Prebuilt browser parser |
| `pseudocode-parser/` | Rust source and golden tests for that parser |
| `tests/` | Node and SQL assertions |
| `docs/` | Design notes, decisions, roadmaps, and research |

The extraction pipeline that created `public/resources` has been archived
outside this repository. Treat the committed corpus as an input; there is no
supported command here to regenerate it.

## Prerequisites

- Node.js 22 and npm. The Node tests use the built-in TypeScript stripping
  supported by Node 22.
- Docker, because the local Supabase stack runs in containers.
- The Supabase CLI. It is included as a development dependency and can be run
  with `npx supabase` or through the npm scripts.
- Rust only when changing or rebuilding `pseudocode-parser`.
- `psql` for direct SQL test execution, or access to the local database
  container as shown below.

## Installation and local setup

Install dependencies and start/reset Supabase:

```bash
npm install
npm run supabase:start
npm run supabase:reset
```

The reset applies every migration and seed. It creates a local development
account with useful sample history:

```text
dev@local.test
devpassword123
```

Run both Edge Functions in their own terminal. The solver and IDE will receive
an error when this process is omitted, even if the rest of Supabase is running:

```bash
npx supabase functions serve
```

Run Vite in a second terminal:

```bash
npm run dev
# http://127.0.0.1:5173
```

Keep the local Supabase stack and functions process running.
The landing page and account flows work without a grading-provider key, but an
IDE submission returns a deliberate 503 until at least one provider is set.

## Configuration

Local Supabase identifiers have checked-in fallbacks, so a plain local setup
does not require `.env`. For a remote project, copy `.env.example` to a local
environment file and replace the project values. Never commit provider keys.

| Variable | Required | Consumer | Meaning |
|---|---|---|---|
| `VITE_SUPABASE_URL` | Remote deploys | Browser | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Remote deploys | Browser | Public/publishable Supabase key |
| `GOOGLE_AI_STUDIO_API_KEY` | One provider key required for grading | `grade` Edge Function | Primary grading provider |
| `OPENROUTER_API_KEY` | One provider key required for grading | `grade` Edge Function | Fallback provider, or the sole provider when Google is unset |

Optional grading overrides are `GOOGLE_AI_MODEL`, `GOOGLE_AI_MODELS`
(comma-separated rotation), `GOOGLE_AI_BASE_URL`,
`GOOGLE_AI_THINKING_BUDGET`, `OPENROUTER_MODEL`,
`OPENROUTER_PROVIDER_ONLY`, `OPENROUTER_PROVIDER_SORT`, and
`OPENROUTER_BASE_URL`. Provider keys belong only in Supabase Function secrets;
variables prefixed with `VITE_` are shipped to browsers. For local functions,
put provider values in an ignored `supabase/functions/.env`; for hosted
functions, use `npx supabase secrets set`.

The grader retries one transient Google failure, then falls back to OpenRouter
for Google rate limits, missing models, network failures, and HTTP
408/500/502/503/504 responses when `OPENROUTER_API_KEY` is configured. Returned
scores are validated for types, non-negative bounds, rubric IDs, per-point
limits, award consistency, and agreement between point totals and the trusted
question maximum before they are persisted.

Local PostgREST is configured for at most 10,000 rows per response. The
per-question topic-practice read also uses exact-count range pagination, so it
remains complete if the hosted project has a lower API row cap; setting the
hosted API maximum to 10,000 avoids extra round trips for long histories.

The Supabase values are not secret credentials. Authorization depends on RLS.
Never add a service-role or secret key to browser or Vercel configuration.
Supabase injects server-only secret credentials into Edge Functions; the code
uses them only for the two service-only persistence RPCs.

OAuth buttons are always rendered, but each provider must also be enabled and
configured in the target Supabase project. The local config does not enable
Google, Azure, or Twitter by default.

## Tests and validation

Run the Node domain/service suite, type check, and production build:

```bash
npm test
npx vue-tsc -b
npm run build
```

The current Node suite contains 129 assertions/tests across `tests/**/*.test.ts`
and `tests/**/*.test.mjs`. The build repeats the type check before Vite bundles
the application.

Run the four SQL suites after `npm run supabase:reset`:

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f tests/test_grading_quota.sql
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f tests/test_solver_rls.sql
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f tests/test_ide_attempts.sql
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f tests/test_trusted_writes.sql
```

If `psql` is not installed on the host, send each file through the local
database container:

```bash
docker exec -i supabase_db_cambridgeparser psql -U postgres -d postgres \
  -v ON_ERROR_STOP=1 < tests/test_grading_quota.sql
docker exec -i supabase_db_cambridgeparser psql -U postgres -d postgres \
  -v ON_ERROR_STOP=1 < tests/test_solver_rls.sql
docker exec -i supabase_db_cambridgeparser psql -U postgres -d postgres \
  -v ON_ERROR_STOP=1 < tests/test_ide_attempts.sql
docker exec -i supabase_db_cambridgeparser psql -U postgres -d postgres \
  -v ON_ERROR_STOP=1 < tests/test_trusted_writes.sql
```

The SQL suites are intentionally separate from `npm test`. They exercise RLS,
ownership, state transitions, quotas, and server-recorded IDE attempts against
a real Postgres/Supabase schema.

When changing the MCQ PDF parser, fetch and run the checksum-pinned solver
golden corpus. The PDFs remain in an ignored local cache:

```bash
node --experimental-strip-types scripts/solver-corpus/fetch.ts
npm ci --prefix supabase/functions/fetch-pdf
node --experimental-strip-types scripts/solver-corpus/validate.ts
```

The corpus covers all 19 solver paper families and distinguishes reviewed
known failures from new regressions. Its selection, truth basis and update
process are documented in
[`tests/fixtures/solver-corpus/README.md`](tests/fixtures/solver-corpus/README.md).

When changing the pseudocode WASM parser, run its separate golden tests:

```bash
cargo test --manifest-path pseudocode-parser/Cargo.toml
```

Automated tests complement rather than replace browser testing. At minimum,
release verification should cover anonymous route guards, account/session
behavior, one complete persisted paper, result review, filtered stats, IDE
parser errors, fill-blank input, grading success/error responses, deep links,
refresh/back navigation, console/network errors, and narrow-screen layouts.

## Build and deployment

`npm run build` creates `dist/`. `vercel.json` applies security/cache headers
and rewrites every route to `index.html` so history-mode deep links work.

A complete deployment has two independently deployed parts:

1. Link the correct Supabase project, apply migrations/seeds as appropriate,
   deploy `fetch-pdf` and `grade`, configure Function secrets and auth
   redirect URLs/OAuth providers, and verify
   RLS with non-admin accounts.
2. Configure only the public browser project values in Vercel, then deploy the
   static web client.

Typical Supabase production commands are:

```bash
npx supabase link --project-ref YOUR_PROJECT_REF
npx supabase db push
npx supabase functions deploy fetch-pdf
npx supabase functions deploy grade
```

Do not run development seeds against production unless that is explicitly
intended. Verify `/dashboard`, `/solver/...`, `/ide/...`, and another deep link
directly on the deployed hostname after deployment; success at `/` alone does
not prove the Vercel rewrite or unified app is live.

## External services and important dependencies

- Supabase Auth, Postgres/PostgREST, RLS/RPCs, and Edge Functions.
- PapaCambridge's public past-paper mirror. Paper availability and upstream
  response time affect solver startup.
- Google AI Studio and OpenRouter. Model availability, quotas, response
  contracts, and keys affect IDE grading. OpenRouter fallback requires its own
  configured key; it cannot help when only Google credentials are present.
- Vercel static hosting and history-route rewrites.
- PDF.js for rendering/annotating papers, CodeMirror for editing, the Rust/WASM
  parser for diagnostics, and ECharts for analytics.

## Known limitations and caveats

- The paper browser is deliberately limited to components the MCQ answer and
  mark-scheme pipeline can parse. It is not a catalogue of every Cambridge
  subject or written paper.
- Paper years and unavailable sittings are curated in
  `src/constants/paperCatalogue.ts`. Update them only after verifying both the
  question paper and mark scheme at the configured mirror.
- Local grading requires `supabase functions serve`. Grading cannot be
  provider-validated without a real
  provider key.
- The WASM parser validates supported pseudocode syntax; it does not currently
  execute programs or produce general program output.
- The dashboard and solver remain desktop-oriented. The dashboard currently
  overflows and overlaps at phone widths, so mobile should not be advertised
  as fully supported until that layout is corrected.
- Paper Generator, Calendar, Settings, profile, copy-question, restart, and
  mid-paper save are explicitly disabled because their workflows are not
  implemented. The solver Overview is a passive state summary, not navigation.
- Password recovery is not exposed because the recovery link has no
  new-password form yet. Do not advertise it until CP-007 in
  `docs/preproduction_issues.md` is resolved.
- PDF.js currently emits repeated localization warnings while valid papers
  render. They are noisy but did not prevent the tested PDFs from loading.
- The committed question corpus is not regenerated in this repository, so
  corpus corrections require an external extraction workflow and a reviewed
  data update.
- The current worktree contains offline Python analysis files outside `api/`, in
  conflict with `AGENTS.md`. Resolve CP-020 before committing those files.

The ranked current issue register, including production gates and evidence, is
[`docs/preproduction_issues.md`](docs/preproduction_issues.md). Older roadmap
documents contain historical pre-merge status and should not be used as the
release checklist.

## Coding constraints

Vue single-file components use `<script setup>`, new code is TypeScript,
indentation is two spaces, values are `camelCase`, and components/types are
`PascalCase`. `erasableSyntaxOnly` is enabled, so use a `const` object plus a
same-named union type instead of `enum` (see `src/lib/types/enums.ts`).

All theme colors come from tokens in `src/styles/themes.scss`; do not define
tokens in `src/styles/ide.css` or hard-code chart palette colors in components.
hand-written files require an `` comment.
