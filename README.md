# CambridgeParser

**cambridgeparser.com** — one application with two halves: a **paper solver** for
Cambridge multiple-choice papers, and a **pseudocode IDE** with mark-scheme
feedback. They share a shell, a sidebar, a theme system, a Supabase project and
an account.

They used to be two separate sites. They are not any more: everything below
`src/` is one Vue app, and the sidebar's page groups are how you move between
them.

## Run it

```bash
npm install
npm run supabase:start     # local stack on :54321
npm run supabase:reset     # migrations + subjects + dev sample data
npm run dev                # http://localhost:5173
```

`npm run supabase:reset` seeds a development account — **dev@local.test /
devpassword123** — with about five months of synthetic attempts, so the stats
page has something to show. No `.env` is needed locally: both the client and the
grading function fall back to the local stack's defaults. See `.env.example` for
a deployed project.

## Layout

| Path | What it is |
|---|---|
| `src/` | **the application.** One Vue 3 + TypeScript app |
| `src/components_dashboard/`, `_browser/`, `_navigator/`, `_stats/` | the paper solver: dashboard, paper browser, the MCQ exam runner, statistics |
| `src/components_ide/`, `src/views/` | the Cambridge IDE: editor, problem explorer, question panel, results — plus the public landing page |
| `src/lib/` | annotation layer, Supabase reads and writes, chart setup, IDE services |
| `src/stores/useAuth.ts` | the one Supabase client and session for the whole app |
| `src/styles/` | `themes.scss` owns every design token; `ide.css` holds the IDE's component styles |
| `src/router/router.ts` | one router, path routing, one guard |
| `api/` | the Vercel Python Function for AI grading. Self-contained — the only Python in the repository |
| `supabase/` | migrations, seeds, edge functions, local CLI config |
| `public/` | the wasm pseudocode parser, question images and record JSON |
| `pseudocode-parser/` | the Rust parser that produces `public/wasm` |
| `docs/` | **[`docs/roadmap.md`](docs/roadmap.md) is the outstanding-work list** |

## Checks

```bash
npm test          # node:test — 15 tests
npx vue-tsc -b    # type check
npm run build     # production bundle
```

## Deployment

Vercel builds `npm run build` to `dist/` and serves `api/grade.py` as
`/api/grade`. Because the app uses path routing, `vercel.json` carries a
catch-all rewrite to `index.html` — without it a deep link like `/ide` 404s
before the app loads.

Environment variables, set in the Vercel dashboard for Production and Preview:

| Variable | Used by |
|---|---|
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | the browser |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | `api/grade.py` (`VITE_` vars are client-only) |
| `GOOGLE_AI_STUDIO_API_KEY`, `OPENROUTER_API_KEY` | the grading providers |

None of the Supabase values are secrets — Row Level Security is what grants
access. Do not add the service-role key; nothing here needs it.

## Conventions

AI-generated code is marked as such: a header block on wholly-generated files,
an `// ` comment on generated lines inside hand-written ones.

`tsconfig` runs with `erasableSyntaxOnly`, so no `enum` — use a `const` object
plus a same-named union type (see `src/lib/types/enums.ts`).
