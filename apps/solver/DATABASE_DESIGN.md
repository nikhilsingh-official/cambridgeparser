<!-- ==========================================================================
     Documentation and proposed SQL only; no application code was changed.
     Subject: SmartSolver's Supabase/Postgres data layer — as-built vs. target.
     ========================================================================== -->

# SmartSolver — Database Design Spec

**Platform: Supabase (Postgres).** Staying. No Firebase migration is assumed anywhere in
this document; the Cambridge IDE will be brought onto Supabase later, and §7.4 notes the
one thing to reserve for it.

**Scope.** Part I documents the data layer exactly as it exists today. Part II derives the
requirements from what the app is for and what it already says it wants to display. Part III
is the target schema. Part IV is the migration. Part V lists what I could not decide for you.

---

# Part I — How it works today

## 1.1 Shape of the current layer

Three tables in `schema.sql`, one client, no server-side logic.

```
auth.users ──< exam_attempts ──< question_attempts
                                        (attempts — orphan table, never referenced)
```

Auth is Supabase Auth (`src/stores/useAuth.ts`): email/password plus Google, Azure and
Twitter OAuth. The client is constructed against a hardcoded `http://127.0.0.1:54321`.

## 1.2 The write path — and it is the only path

Everything happens in one burst at `endExam()` (`src/components_navigator/MCQNav.vue`):

```
endExam()
  └─ getQuestionsAnalytics(highlights, focusAreas, answers)   → per-question facts
  └─ enrichAnalytics(questionsData, eventLogs)                → weighted scores
  └─ pushToExamTable(...)      → INSERT exam_attempts      → returns id
  └─ pushToAttemptsTable(...)  → UPSERT question_attempts  (on exam_attempt_id, question_number)
```

**The application performs no reads.** Audited across `src/`: the only `supabase.*` calls
are the five auth calls in `useAuth.ts` and `supabase.functions.invoke("fetch-pdf")` in
`MCQNav.vue`. There is not one `.select()` outside the write path's `.select()` chaining.

That single fact explains the state of the stats page: **every number it shows is fabricated
in the component**, because there is no query layer to show anything else.

## 1.3 What is captured but never persisted

| Produced by | Value | Fate |
|---|---|---|
| `getQuestionsAnalytics` | `qCorrect` — whether the answer was right | **discarded**; no column exists |
| `fetch-pdf` edge function | `answers[]` — the parsed mark-scheme key (question, answer, marks) | **discarded** after grading in-memory |
| `addEventLog` | `eventLogs[]` — the full interaction stream (~50–200 events/paper) | **discarded**; only aggregates survive |
| `addEventLog` | `timezone` (IANA, per event) | **discarded** |
| `addEventLog` | `dateTimestamp`, `performanceTimestamp` per event | **discarded** |

## 1.4 Defects in the as-built layer

Each is a code-level fact, with its location.

**D1 — Correctness is never stored.** `pushToAttemptsTable.ts` builds a 20-field payload
that omits `q.qCorrect`, and `schema.sql` has no column for it. Accuracy, scores, marks,
"strongest subject" and every derivative are **unobtainable from the database**, not merely
un-implemented.

**D2 — `time_spent_ms` holds seconds.** `startFocusAreaTimer.ts` accumulates
`active.time += deltaSeconds`. `pushToAttemptsTable.ts:16` writes `Math.round(q.time ?? 0)`
straight into `time_spent_ms`. Meanwhile `hesitation_time_ms` (from `performance.now()`
deltas) and `exam_attempts.total_time_ms` (`performance.now() - perfStart`) are true
milliseconds. **Two columns in one schema, both suffixed `_ms`, differing by 1000×.**

**D3 — The `marked_*_count` columns cannot hold a count.** `enrichAnalytics` computes real
counts (`flagCount`, `difficultCount`, `saveCount`), then `pushToAttemptsTable.ts:18–20`
writes `q.markedForReview ? 1 : 0`. Three `integer` columns named `_count` are structurally
limited to `{0, 1}`. (Moot today — see D4 — but it will bite the moment D4 is fixed.)

**D4 — The flag buttons emit nothing.** `ActiveQuestionButtons.vue` renders Copy/Flag/Star/Save
with no click handlers and no `addEventLog` call, so all three counts are permanently 0. In
`enrichAnalytics` that pins `markReviewScore`/`markDifficultScore`/`markSaveScore` at 1,
which are 0.4 of confidence, 0.4 of difficulty and 0.35 of interest. **Three of the headline
metrics are largely constant in every row ever written.**

**D5 — No RLS.** No `alter table … enable row level security`, no policies. Under Supabase's
default-deny the client cannot read these tables on a real project at all; the write path
works locally only because the dev stack is permissive. This is simultaneously a
"nothing works in production" bug and, if RLS were merely enabled without policies, a
"everything is readable" risk depending on which key is used.

**D6 — `paper_id` is a composite key smuggled into a string.** `'0625_s25_22'` encodes
subject `0625`, season `s`, year `25`, paper `2`, variant `2` — validated by
`/^\d+_[a-z]\d{2}_\d+$/` in the edge function. Nothing is indexable or groupable: every
per-subject or per-year statistic requires the client to string-parse every row.

**D7 — Derived scores are stored with no algorithm version.** `confidence`, `difficulty`
and `interest` come from hardcoded weight vectors in `enrichAnalytics.ts`
(`[0.4,0.3,0.2,0.1]`, `[0.4,0.25,0.2,0.1,0.05]`, `[0.35,0.25,0.15,0.05,0.05,0.15]`). Those
weights are estimates and will be tuned. Because the inputs are discarded (§1.3), **tuning
them silently makes old rows incomparable with new ones and there is no way to detect it,
let alone recompute.**

**D8 — Abandoned attempts are invisible.** The `exam_attempts` row is inserted only inside
`endExam()`. A paper opened and quit is never recorded. So "papers started", completion rate
and resume are all impossible, and `started_at` is client-supplied at end time rather than
observed at start.

**D9 — Correctness would be client-asserted.** Even once D1 is fixed, `qCorrect` is computed
in the browser against an answer key the browser downloaded. A user can trivially write
`is_correct = true` for every row. Irrelevant for a private tool; disqualifying the moment
there is a leaderboard, a shared class view, or a second user.

**D10 — Local-time concepts stored only in UTC.** `started_at` is `timestamptz`. "Practice
streak" and "peak solving hour" are local-calendar concepts. The timezone is captured on
every event and thrown away (§1.3), so these cannot be computed correctly for a user who
travels — or, more mundanely, who studies after 23:00 in UTC+5.

**D11 — Dead table.** `attempts` (generic `attempt_type` + `metadata jsonb`) is referenced
nowhere in `src/`.

**D12 — Four options hardcoded.** `check (selected_option between 0 and 3)` and
`eliminated_options_mask between 0 and 15`. Fine for IGCSE A–D; blocks any paper with a
different option count without a schema migration.

## 1.5 The decisive audit: what the app already says it wants

`src/constants/codeMaps.ts` declares `categoryToText` — 17 statistics the UI is built to
display, each with an icon and a subject-specific flag. This is the read requirement, stated
by your own code. Scored against the current schema:

| # | Statistic | Servable today? | Blocker |
|---|---|---|---|
| 0 | Your Top Subject | ❌ | D1 (needs accuracy), D6 |
| 1 | Total Papers Solved | ⚠️ | works, but "solved" is undefined — D8 |
| 2 | Total Time Solving | ✅ | — |
| 3 | Overall Accuracy | ❌ | **D1** |
| 4 | Practice Streak | ⚠️ | D10 — streak boundaries wrong outside UTC |
| 5 | Strongest Subject | ❌ | D1, D6 |
| 6 | Most Improved Subject | ❌ | D1, D6 |
| 7 | Most Attempted Subject | ⚠️ | D6 — client must string-parse |
| 8 | This Week's Accuracy | ❌ | D1, D10 |
| 9 | This Week's Solving Time | ⚠️ | D10 |
| 10 | Time Since Last Paper | ✅ | — |
| 11 | Fastest Completion Time | ⚠️ | D8 — partial attempts pollute |
| 12 | Longest Session | ✅ | — |
| 13 | Peak Solving Hour | ❌ | **D10** |
| 14 | Next Goal | ❌ | no goals table |
| 15 | Improvement Rate | ❌ | D1, D7 |
| 16 | Performance Overview | ❌ | D1 |

**3 of 17 clean, 5 compromised, 9 impossible.** Eight of the nine impossible ones are
blocked by a single missing boolean.

---

# Part II — What the layer has to do

## 2.1 Purpose

Students sit Cambridge MCQ past papers in the browser against the real PDF, are marked
automatically from the mark scheme, and get back not just a score but a behavioural read of
*how* they answered — time per question, hesitation, how decisively they eliminated
distractors, what they revisited, what they flagged. The value is the second part; a score
alone is a mark scheme.

Three consumers:

1. **Solver** (`components_navigator/`) — writes an attempt.
2. **Stats** (`components_stats/`) — reads the 17 statistics in §1.5, overall and per subject,
   over time.
3. **Browser** (`components_browser/`) — lists papers to attempt, ideally annotated with the
   user's history against each.

## 2.2 Design principles

**P1 — Store observations, derive metrics.** Raw events are cheap (~200 rows/paper, tens of
bytes each) and are the only thing that makes D7 recoverable. Every weighted score must be
reproducible from stored inputs. This is the single most consequential change in this spec.

**P2 — Separate facts from weighted composites.** `revisit_count` is a fact: count the
events, get the same answer forever. `confidence` is a judgement: it depends on tunable
weights *and* on `meanTime` across the whole paper, so it changes when the formula changes
or when a sibling question changes. Different lifecycles, different tables.

**P3 — Version anything derived.** Every composite carries the algorithm version that
produced it, so old and new can coexist and be compared honestly.

**P4 — The server owns the truth about correctness.** The client says which option was
picked. The database decides whether that was right, by joining an answer key the client
never wrote. Closes D9 and D1 together.

**P5 — Identity is columns, not string parsing.** Subject, series, year, paper and variant
are queryable fields.

**P6 — Deny by default.** RLS on every table, policy per table, user scoped to their own rows.

**P7 — Local time is data.** Store the IANA zone and the local date; do not re-derive them
from UTC.

---

# Part III — Target schema

## 3.1 Overview

```
                        subjects
                            │
                            ▼
auth.users ──> profiles   papers ──< paper_questions
     │                      │              │
     └──< exam_attempts ────┘              │
                │                          │
                ├──< question_attempts ────┘   (facts; is_correct computed server-side)
                │           │
                │           └──< question_metrics      (weighted composites, versioned)
                │
                └──< attempt_events                    (raw interaction stream)

auth.users ──< goals                                   (for "Next Goal")
```

Reference data (`subjects`, `papers`, `paper_questions`) is world-readable and
service-written. User data is private to its owner.

## 3.2 Reference tables

```sql
create extension if not exists pgcrypto;

-- Seeded from src/constants/codeMaps.ts (33 subjects today).
create table subjects (
  code          text primary key,              -- '0625'
  name          text not null,                 -- 'Physics'
  qualification text not null default 'IGCSE', -- 'IGCSE' | 'A Level' | ...
  icon_slug     text,                          -- lucide name; SVG stays in the client
  created_at    timestamptz not null default now()
);

create type exam_series as enum ('m', 's', 'w');   -- Feb/Mar, May/Jun, Oct/Nov

create table papers (
  id            uuid primary key default gen_random_uuid(),
  subject_code  text not null references subjects(code),
  series        exam_series not null,
  year          smallint not null check (year between 2000 and 2100),
  paper_number  smallint not null,             -- the '2' of paper 22
  variant       smallint not null,             -- the '2' of paper 22
  -- '0625_s25_22' — the URL/route identifier, kept as a real unique key
  schema_code   text not null unique,
  question_count smallint,
  answers_source_url text,                     -- provenance of the key
  answers_parsed_at  timestamptz,              -- null = key not yet cached
  created_at    timestamptz not null default now(),
  unique (subject_code, series, year, paper_number, variant)
);

-- The answer key, cached once from the mark-scheme PDF instead of re-parsed per attempt.
create table paper_questions (
  id             uuid primary key default gen_random_uuid(),
  paper_id       uuid not null references papers(id) on delete cascade,
  question_number smallint not null,
  correct_option smallint not null check (correct_option >= 0),  -- 0=A
  option_count   smallint not null default 4 check (option_count between 2 and 8),
  marks          smallint not null default 1,
  topic          text,                          -- optional syllabus tag, later
  unique (paper_id, question_number)
);
```

Caching the key (rather than discarding it as today) buys four things: correctness can be
computed server-side (P4); attempts stop re-downloading and re-parsing the mark scheme;
past attempts survive papacambridge going away; and a mis-parsed key can be corrected once,
after which every affected attempt can be re-marked.

`option_count` retires D12.

## 3.3 User tables

```sql
create table profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  timezone     text not null default 'UTC',    -- IANA, e.g. 'Asia/Kolkata'
  created_at   timestamptz not null default now()
);

create type attempt_status as enum ('in_progress', 'completed', 'abandoned');

create table exam_attempts (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  paper_id        uuid not null references papers(id),
  status          attempt_status not null default 'in_progress',
  started_at      timestamptz not null default now(),
  finished_at     timestamptz,
  duration_ms     integer check (duration_ms >= 0),     -- milliseconds. Genuinely.
  client_timezone text not null default 'UTC',
  -- Written by the client at insert. NOT a generated column: `at time zone <column>`
  -- is STABLE, not IMMUTABLE, so Postgres will not accept it in a generated expression.
  local_date      date not null,
  metrics_version smallint not null default 1,
  created_at      timestamptz not null default now()
);

create index on exam_attempts (user_id, started_at desc);
create index on exam_attempts (user_id, paper_id);
create index on exam_attempts (user_id, local_date);
create index on exam_attempts (user_id, status);
```

The row is now created at **exam start** with `status='in_progress'` and updated at end.
That fixes D8, makes resume possible, and makes `started_at` an observation instead of a
client claim.

### Facts — what the student did

```sql
create table question_attempts (
  id                uuid primary key default gen_random_uuid(),
  exam_attempt_id   uuid not null references exam_attempts(id) on delete cascade,
  question_number   smallint not null,

  selected_option   smallint check (selected_option >= 0),   -- null = unanswered
  eliminated_mask   smallint not null default 0,             -- bit i set = option i eliminated

  -- Authoritative. Set by trigger against paper_questions; never accepted from the client.
  is_correct        boolean,

  time_spent_ms     integer not null default 0 check (time_spent_ms >= 0),
  hesitation_ms     integer check (hesitation_ms >= 0),

  option_switch_count        smallint not null default 0,
  elimination_reversal_count smallint not null default 0,
  revisit_count              smallint not null default 0,
  marked_for_review_count    smallint not null default 0,
  marked_as_difficult_count  smallint not null default 0,
  marked_for_save_count      smallint not null default 0,

  stable_elimination_ratio real not null default 0
      check (stable_elimination_ratio between 0 and 1),
  exploration_depth   smallint not null default 0,
  exploration_breadth smallint not null default 0,

  created_at timestamptz not null default now(),
  unique (exam_attempt_id, question_number)
);

create index on question_attempts (exam_attempt_id);
create index on question_attempts (exam_attempt_id, is_correct);
```

The bitmask encoding is retained from the current schema — it is compact and already
implemented by `lettersToMask.ts`. The `0..15` ceiling is dropped so `option_count > 4`
works.

`marked_*_count` are `smallint` counts and **must be written as counts** — fixing D3 is one
line in `pushToAttemptsTable.ts` (`q.markedForReview ?? 0`, not `q.markedForReview ? 1 : 0`).

### Server-side marking (closes D1, D4-adjacent and D9)

```sql
create or replace function set_question_correctness() returns trigger
language plpgsql security definer as $$
begin
  select (pq.correct_option = new.selected_option)
    into new.is_correct
  from paper_questions pq
  join exam_attempts ea on ea.id = new.exam_attempt_id
  where pq.paper_id = ea.paper_id
    and pq.question_number = new.question_number;

  -- No cached key, or unanswered: leave null rather than guess.
  if new.selected_option is null then
    new.is_correct := null;
  end if;
  return new;
end $$;

create trigger trg_question_correctness
  before insert or update of selected_option, question_number
  on question_attempts
  for each row execute function set_question_correctness();
```

`is_correct` becomes null-if-unknown, true, or false — and the client cannot set it.
A re-mark after fixing a bad answer key is then just
`update question_attempts set selected_option = selected_option where …`.

### Derived composites — versioned (P2, P3)

```sql
create table question_metrics (
  question_attempt_id uuid not null references question_attempts(id) on delete cascade,
  metrics_version     smallint not null,
  confidence real not null check (confidence between 0 and 1),
  difficulty real not null check (difficulty between 0 and 1),
  interest   real not null check (interest   between 0 and 1),
  computed_at timestamptz not null default now(),
  primary key (question_attempt_id, metrics_version)
);

-- What each version actually was, so a score is interpretable years later.
create table metrics_versions (
  version     smallint primary key,
  description text not null,
  weights     jsonb not null,      -- {"confidence":[0.4,0.3,0.2,0.1], "difficulty":[...], ...}
  created_at  timestamptz not null default now()
);
```

Seed `version = 1` with the weight vectors currently hardcoded in `enrichAnalytics.ts`.
Retuning becomes: insert version 2, recompute from `attempt_events`, keep both.

These three live apart from `question_attempts` for a concrete reason: they depend on
`meanTime`/`meanNorm`/`stdNorm` **across the whole paper**, so adding or correcting one
question's timing changes every other question's score in that attempt. They are not
properties of a single response.

### Raw events (P1) — the thing that is currently thrown away

```sql
create type event_element as enum ('highlight', 'focusArea', 'Copy', 'Flag', 'Star', 'Save');

create table attempt_events (
  id              bigserial primary key,
  exam_attempt_id uuid not null references exam_attempts(id) on delete cascade,
  seq             integer not null,             -- client ordinal; breaks timestamp ties
  question_number smallint,
  element_type    event_element not null,
  action_type     text not null,                -- 'setCorrect' | 'userClick' | 'Selection' | ...
  option_index    smallint,
  -- ms since exam start, from performance.now() — monotonic, immune to clock changes
  elapsed_ms      integer not null check (elapsed_ms >= 0),
  occurred_at     timestamptz not null,
  unique (exam_attempt_id, seq)
);

create index on attempt_events (exam_attempt_id, question_number);
create index on attempt_events (exam_attempt_id, element_type);
```

Maps 1:1 onto the existing `EventLogs` type, with two corrections:

- `elapsed_ms` is normalised to *ms since exam start*, not raw `performance.now()`
  (ms since page load, which is what `addEventLog` records today). `enrichAnalytics` only
  uses differences so it never noticed; stored across sessions the raw value is meaningless.
- The per-event `timezone` string is dropped — it belongs on the attempt, not repeated
  ~200 times per paper.

`action_type` stays `text` rather than an enum: the vocabulary in `utilsTypes.ts`
(`setCorrect`, `elimToCorrect`, `deselectedCorrect`, `correctToElim`, `setElim`,
`deselectedElim`, `userClick`, `userHoveredIn`, `userHoveredOutPage`, `Selection`,
`Deselection`) is still churning, and an enum makes every addition a migration.

**Volume:** ~200 events × ~40 bytes ≈ 8 KB per paper. A thousand papers is 8 MB. This is
free relative to what it enables.

### Goals — for statistic #14

```sql
create type goal_kind as enum ('papers_per_week', 'accuracy_target', 'subject_focus', 'streak_days');

create table goals (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  kind         goal_kind not null,
  subject_code text references subjects(code),   -- null = all subjects
  target       numeric not null,
  active       boolean not null default true,
  created_at   timestamptz not null default now()
);

create index on goals (user_id) where active;
```

## 3.4 Read layer

Views, not materialised views. At one-student scale with the indexes above these are
milliseconds; materialise only if measurement says so.

```sql
-- One row per attempt, with score. Feeds #1, #2, #11, #12 and the browser's history badges.
create view v_attempt_summary as
select
  ea.id, ea.user_id, ea.status, ea.started_at, ea.finished_at,
  ea.duration_ms, ea.local_date,
  p.schema_code, p.subject_code, p.series, p.year, p.paper_number, p.variant,
  s.name as subject_name,
  count(qa.id)                                            as questions_answered,
  count(*) filter (where qa.is_correct)                   as questions_correct,
  round(avg((qa.is_correct)::int)::numeric, 4)            as accuracy,
  avg(qa.time_spent_ms)::int                              as avg_time_per_question_ms
from exam_attempts ea
join papers   p on p.id = ea.paper_id
join subjects s on s.code = p.subject_code
left join question_attempts qa on qa.exam_attempt_id = ea.id
group by ea.id, p.id, s.name;

-- Feeds #4 practice streak, #8/#9 this-week, #13 peak hour (local, per P7).
create view v_daily_activity as
select
  ea.user_id,
  ea.local_date,
  count(distinct ea.id)                  as papers,
  sum(ea.duration_ms)                    as total_time_ms,
  count(qa.id)                           as questions,
  count(*) filter (where qa.is_correct)  as correct,
  mode() within group (
    order by extract(hour from ea.started_at at time zone ea.client_timezone)
  )                                      as modal_local_hour
from exam_attempts ea
left join question_attempts qa on qa.exam_attempt_id = ea.id
where ea.status = 'completed'
group by ea.user_id, ea.local_date;

-- Feeds #0, #5, #6, #7 and the per-subject stats sections.
create view v_subject_stats as
select
  ea.user_id,
  p.subject_code,
  s.name as subject_name,
  count(distinct ea.id)                        as attempts,
  round(avg((qa.is_correct)::int)::numeric, 4) as accuracy,
  sum(ea.duration_ms)                          as total_time_ms,
  max(ea.finished_at)                          as last_attempt_at,
  avg(qm.confidence)                           as avg_confidence,
  avg(qm.difficulty)                           as avg_difficulty,
  avg(qm.interest)                             as avg_interest
from exam_attempts ea
join papers   p on p.id = ea.paper_id
join subjects s on s.code = p.subject_code
left join question_attempts qa on qa.exam_attempt_id = ea.id
left join question_metrics  qm on qm.question_attempt_id = qa.id
                              and qm.metrics_version = ea.metrics_version
where ea.status = 'completed'
group by ea.user_id, p.subject_code, s.name;
```

Note the join on `qm.metrics_version = ea.metrics_version` — that is P3 doing its job:
an attempt is always read back with the algorithm it was scored under.

**Coverage after this: all 17 of §1.5.** #6 "Most Improved" and #15 "Improvement Rate" come
from windowing `v_attempt_summary.accuracy` over `started_at` per subject; #14 from `goals`
against `v_daily_activity`; #16 from `v_subject_stats`.

## 3.5 Row-level security (P6)

```sql
alter table profiles          enable row level security;
alter table exam_attempts     enable row level security;
alter table question_attempts enable row level security;
alter table question_metrics  enable row level security;
alter table attempt_events    enable row level security;
alter table goals             enable row level security;
alter table subjects          enable row level security;
alter table papers            enable row level security;
alter table paper_questions   enable row level security;

-- Reference data: readable by any signed-in user, writable only by the service role
-- (the edge function that caches answer keys). No policy for write ⇒ denied to clients.
create policy read_subjects        on subjects        for select to authenticated using (true);
create policy read_papers          on papers          for select to authenticated using (true);
create policy read_paper_questions on paper_questions for select to authenticated using (true);

-- Own profile.
create policy own_profile on profiles
  for all to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- Own attempts.
create policy own_attempts on exam_attempts
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Children: ownership proven by joining up to the attempt.
create policy own_question_attempts on question_attempts
  for all to authenticated
  using      (exists (select 1 from exam_attempts ea
                      where ea.id = question_attempts.exam_attempt_id and ea.user_id = auth.uid()))
  with check (exists (select 1 from exam_attempts ea
                      where ea.id = question_attempts.exam_attempt_id and ea.user_id = auth.uid()));

create policy own_attempt_events on attempt_events
  for all to authenticated
  using      (exists (select 1 from exam_attempts ea
                      where ea.id = attempt_events.exam_attempt_id and ea.user_id = auth.uid()))
  with check (exists (select 1 from exam_attempts ea
                      where ea.id = attempt_events.exam_attempt_id and ea.user_id = auth.uid()));

create policy own_question_metrics on question_metrics
  for all to authenticated
  using      (exists (select 1 from question_attempts qa
                      join exam_attempts ea on ea.id = qa.exam_attempt_id
                      where qa.id = question_metrics.question_attempt_id and ea.user_id = auth.uid()))
  with check (exists (select 1 from question_attempts qa
                      join exam_attempts ea on ea.id = qa.exam_attempt_id
                      where qa.id = question_metrics.question_attempt_id and ea.user_id = auth.uid()));

create policy own_goals on goals
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
```

Views inherit the RLS of their base tables when created by a non-superuser owner. Create
them as a normal role, or declare them `security_invoker = true` (PG15+), so a view cannot
become a hole around the policies above.

**`paper_questions` is deliberately client-readable.** A determined user can therefore read
the answer key before answering. That is unavoidable while the client also fetches the
mark-scheme PDF, and it does not matter for self-study — but it means these numbers must
never be treated as invigilated. See §5.3.

---

# Part IV — Migration

## 4.1 Recommended: rebuild

The current data is local-dev only, is written by a path with D2 (wrong units) and D3
(destroyed counts), and carries no correctness. **It is not worth migrating.**
`supabase db reset` against the new `schema.sql`, then re-seed `subjects` and `papers`.

If real attempts do exist, they can be carried across with
`time_spent_ms → time_spent_ms * 1000` and `is_correct` left null (unknowable — the key was
never stored), but they will be missing from every accuracy statistic. Cleaner to archive
the old tables under a `legacy_` prefix and start clean.

## 4.2 Order of work

| Step | Change | Unblocks |
|---|---|---|
| 1 | Apply the new schema; seed `subjects` from `codeMaps.ts`; enable RLS | D5, D6, D11, D12 |
| 2 | Edge function caches parsed answers into `papers`/`paper_questions` on first fetch | D1 (data), removes re-parsing |
| 3 | Correctness trigger | **D1, D9** |
| 4 | Create the attempt at exam start; update at end | D8 |
| 5 | Fix `time_spent_ms` to write milliseconds | **D2** |
| 6 | Fix `marked_*_count` to write counts, not booleans | D3 |
| 7 | Wire `ActiveQuestionButtons.vue` → `handleButtonClick` → `addEventLog` | **D4** |
| 8 | Persist `attempt_events`; seed `metrics_versions` v1; write `question_metrics` | D7 |
| 9 | Move the Supabase URL/key to `VITE_SUPABASE_*` | §1.1 |
| 10 | Build the query layer + views; replace the placeholder data in `components_stats/` | the stats page |

Steps 5 and 6 are one-line changes in `pushToAttemptsTable.ts`. Step 7 is the only one that
touches a component's behaviour, and the logic already exists in
`src/lib/buttons/handleButtonClick.ts`.

**Do steps 5–7 before step 10.** Building the stats page on top of seconds-labelled-as-ms,
booleans-labelled-as-counts and permanently-zero flag counts means shipping charts that are
confidently wrong.

## 4.3 Client changes implied

| File | Change |
|---|---|
| `src/lib/supabase/pushToExamTable.ts` | split into `startExamAttempt()` / `finishExamAttempt()`; send `client_timezone`, `local_date` |
| `src/lib/supabase/pushToAttemptsTable.ts` | drop `is_correct` (server-owned); fix ms; fix counts; write `question_metrics` separately |
| `src/lib/supabase/` (new) | `pushEventLogs.ts` — bulk insert `attempt_events` |
| `src/lib/supabase/` (new) | `queries/` — the read layer the app has never had |
| `src/lib/utils/addEventLog.ts` | record `elapsed_ms` relative to exam start; add a `seq` counter |
| `src/components_navigator/ActiveQuestionButtons.vue` | wire the four buttons to `handleButtonClick` |
| `src/stores/useAuth.ts` | env-driven URL/key; upsert `profiles` (incl. timezone) on first sign-in |

---

# Part V — Open decisions

**5.1 Where do metrics get computed?** Kept client-side above (smallest change). Moving
`enrichAnalytics` into a Postgres function or an edge function would make recomputation
across all history a single statement rather than a client backfill. Recommend leaving it
client-side until you actually retune weights the first time — that is when the cost lands.

**5.2 Syllabus topics.** `paper_questions.topic` is a placeholder. Per-topic mastery
("you lose marks on electromagnetism") is the natural next metric and the most valuable
one not in the §1.5 list, but it needs a topic taxonomy per subject and a per-question
mapping that nothing currently produces. The `corpus/syllabus_papers/` set in this repo
is the obvious raw material.

**5.3 Multi-user.** Everything above is single-user-correct. Class/leaderboard features
would need the answer key kept away from the client (server-side marking of a submitted
answer sheet), which is a different fetch-pdf design. Worth deciding before, not after.

**5.4 Retention of `attempt_events`.** Unbounded growth is fine at personal scale. If it
ever isn't, the rule is: keep events for the newest N attempts per user, keep
`question_attempts` forever — facts are small, events are the bulky recomputation substrate.

**5.5 The dead `attempts` table.** Assumed dropped. If it was scaffolding for a future
non-MCQ attempt type (pseudocode questions from the Cambridge IDE, say), say so and it
should be designed properly rather than left as an untyped `jsonb` bag — most likely as a
sibling `pseudocode_attempts` table sharing `exam_attempts` as a parent.
