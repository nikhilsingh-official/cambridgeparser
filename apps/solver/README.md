
# Soluer — the CambridgeParser paper solver

A Vue 3 + TypeScript app for sitting Cambridge multiple-choice papers against the
real PDF: highlight and eliminate options on the page itself, get timed per-question
focus areas, and have every interaction recorded for the stats layer.

Part of the [CambridgeParser](../../README.md) monorepo. Merged in from its own
repository with full history — see `docs/merge_notes.md` for what came from where.

## Run it

```bash
npm install
cp ../../.env.example ../../.env   # one .env at the repo root serves both apps
npm run dev                        # http://localhost:5173
```

Every route requires authentication. From the repository root, `npm run supabase:start` brings up the local stack
and `npm run supabase:reset` applies the migrations and seeds:

```bash
psql "$SUPABASE_DB_URL" -f ../../supabase/seeds/seed_subjects.sql
```

> The DDL in `supabase/migrations/` has never been executed against a live
> database — see `docs/future_work.md` §2.1 before trusting it.

## Checks

```bash
npm test          # node:test over tests/**/*.test.ts
npx vue-tsc -b    # type check
npx vite build    # production bundle
```

## Layout

| Path | What lives there |
|---|---|
| `src/components_navigator/` | the exam runner — `MCQNav.vue` orchestrates the PDF iframe, highlights, focus areas, timers |
| `src/components_stats/` | the stats page (still on placeholder data — `docs/future_work.md` §2.4) |
| `src/components_auth/` | login and the auth-gated shell |
| `src/lib/highlights/`, `src/lib/focusAreas/`, `src/lib/render/` | the annotation layer drawn over pdf.js |
| `src/lib/supabase/` | writes (`push*.ts`) and the read layer (`queries/`) |
| `src/lib/state/examState.ts` | the reactive per-question projection the Overview panel reads |
| `src/styles/themes.scss` | the three selectable themes, shared with the pseudocode IDE |
| `../../supabase/` | shared with the IDE: migrations, seeds, edge functions, CLI config |
| `corpus/`, `legacy/` | scraped syllabus reference data, and the superseded pre-merge apps |

## Conventions

AI-generated code is marked as such — a header block on wholly-generated files,
an `// ` comment on generated lines inside hand-written ones. Keep that up.

`tsconfig` runs with `erasableSyntaxOnly`, so no `enum`: use a `const` object plus
a same-named union type (see `src/lib/types/enums.ts`).
