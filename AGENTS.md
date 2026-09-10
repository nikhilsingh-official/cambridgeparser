# Repository Guidelines

## Project Structure & Module Organization

This repository is **one application**: cambridgeparser.com, a Vue 3 +
TypeScript app containing both the MCQ paper solver and the Cambridge pseudocode
IDE. They were separate sites once; do not reintroduce that split.

- `src/` is the whole application. `main.ts` mounts it, `router/router.ts` is the
  single router, `stores/useAuth.ts` is the single Supabase client and session.
- `src/components_dashboard/`, `_browser/`, `_navigator/`, `_stats/` are the
  solver's pages. `src/components_ide/` and `src/views/` are the IDE's, plus the
  public landing page.
- `src/lib/` holds non-component logic: the PDF annotation layer, Supabase reads
  (`supabase/queries/`) and writes (`supabase/push*.ts`), chart setup, and the
  IDE's services under `lib/ide/`.
- `src/styles/themes.scss` is the **single source of design tokens** for all
  three themes. `src/styles/ide.css` holds the IDE's component styles and must
  not define tokens.
- `api/` is the only Python: a self-contained Vercel Function for AI grading. It
  imports nothing outside `api/`.
- `supabase/` holds migrations (applied in filename order), seeds, the
  `fetch-pdf` edge function and `config.toml`.
- `public/` holds the wasm parser and the question corpus the IDE reads.
- `pseudocode-parser/` is the Rust source for `public/wasm`.

The corpus extraction pipeline that produced `public/resources` was Python and
has been archived outside the repository; its output is committed and no longer
regenerated here.

## Build, Test, and Development Commands

- `npm run dev` — the app on :5173.
- `npm run supabase:start` then `npm run supabase:reset` — local stack,
  migrations, subject seed and the dev sample data (`dev@local.test` /
  `devpassword123`).
- `npm test` — `node:test` over `tests/**` (15 tests).
- `npx vue-tsc -b` — type check. `npm run build` runs it before building.
- `psql "$SUPABASE_DB_URL" -f tests/test_grading_quota.sql` — the SQL assertions;
  these are not part of `npm test`.

## Coding Style & Naming Conventions

Two-space indent, `camelCase` values, `PascalCase` components and types. Vue SFCs
use `<script setup>`; TypeScript where the file is new.

`erasableSyntaxOnly` is on, so **no `enum`** — use a `const` object plus a
same-named union type (`src/lib/types/enums.ts`).

Chart colours come from the `--series-*` and `--seq-*` tokens, never hex in a
component. Validate any new palette rather than choosing by eye.

## Testing Guidelines

Name files `*.test.ts` or `*.test.mjs` under `tests/`. Prefer testing the seam
that would silently produce a wrong number over testing a render.

## Commit & Pull Request Guidelines

Concise imperative subjects, optionally scoped — `stats: build the page`,
`auth: move the IDE to Supabase`. Explain *why* in the body, and state what was
verified and what was not.

Do not add authorship-attribution headers or inline authorship markers to
generated or edited files.

## Security & Configuration Tips

Neither Supabase value in `.env` is a secret; RLS is what grants access. The
service-role key is deliberately absent — nothing here needs it, and `api/`
is built to hold no admin credential. Never commit provider API keys.
