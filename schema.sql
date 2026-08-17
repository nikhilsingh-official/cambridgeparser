-- ==========================================================================
--
-- SmartSolver schema, rewritten from the original three-table version.
-- Implements the fixes agreed in DATABASE_DESIGN.md:
--   D1  correctness is stored, and computed server-side from a cached key
--   D2  time columns are genuinely milliseconds
--   D3  marked_* are real counts
--   D6  paper_id stays the ground-truth Cambridge string; structure is
--       DERIVED from it via generated columns (no second source of truth)
--   D7  the raw event stream is persisted; derived scores are versioned
--   D8  attempts have a lifecycle (in_progress -> completed / abandoned)
--   D10 local timezone and local date are stored, not re-derived from UTC
--   D11 the unused `attempts` table is dropped
--   D12 option count is per-question, not hardcoded to 4
--
-- DELIBERATELY NOT INCLUDED: row-level security. Running on local emulators
-- for now; RLS lands before production. See FUTURE_WORK.md.
--
-- Apply with:  supabase db reset   (then psql -f supabase/seed_subjects.sql)
-- ==========================================================================

create extension if not exists pgcrypto;

-- --------------------------------------------------------------------------
-- Reference data
-- --------------------------------------------------------------------------

-- Populated by supabase/seed_subjects.sql (196 rows scraped from Cambridge).
create table if not exists subjects (
  code          text primary key,                     -- '0625', '9618'
  name          text not null,                        -- 'Physics'
  qualification text not null,                        -- 'IGCSE' | 'O Level' | 'AS/A Level'
  is_legacy     boolean not null default false,       -- withdrawn but still in past papers
  created_at    timestamptz not null default now()
);

-- Syllabus topics. INTENTIONALLY EMPTY - to be filled in per subject.
-- See src/constants/topicMap.ts for the fill-in-the-blank client-side map and
-- the loader that seeds this table from it.
create table if not exists topics (
  id           uuid primary key default gen_random_uuid(),
  subject_code text not null references subjects(code) on delete cascade,
  code         text not null,                         -- '4.1', 'em-induction'
  name         text not null,                         -- 'Electromagnetic induction'
  parent_code  text,                                  -- for a 2-level taxonomy
  sort_order   smallint not null default 0,
  unique (subject_code, code)
);

create index if not exists idx_topics_subject on topics(subject_code);

-- --------------------------------------------------------------------------
-- Answer keys, cached from the mark-scheme PDF the first time a paper is sat.
-- Previously parsed on every attempt and thrown away, which made re-marking
-- impossible and put correctness in the browser's hands.
-- --------------------------------------------------------------------------
create table if not exists paper_answer_keys (
  paper_id     text primary key,                      -- '0625_s25_22'
  source_url   text,
  question_count smallint,
  parsed_at    timestamptz not null default now()
);

create table if not exists paper_answers (
  paper_id        text not null references paper_answer_keys(paper_id) on delete cascade,
  question_number smallint not null,
  correct_option  smallint not null check (correct_option >= 0),  -- 0=A, 1=B, ...
  option_count    smallint not null default 4 check (option_count between 2 and 8),
  marks           smallint not null default 1,
  topic_id        uuid references topics(id) on delete set null,  -- filled in later
  primary key (paper_id, question_number)
);

create index if not exists idx_paper_answers_topic on paper_answers(topic_id);

-- --------------------------------------------------------------------------
-- Users
-- --------------------------------------------------------------------------
create table if not exists profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  timezone     text not null default 'UTC',           -- IANA, e.g. 'Asia/Kolkata'
  created_at   timestamptz not null default now()
);

do $$ begin
  create type attempt_status as enum ('in_progress', 'completed', 'abandoned');
exception when duplicate_object then null; end $$;

-- --------------------------------------------------------------------------
-- Attempts
--
-- paper_id remains the Cambridge identifier verbatim - it is the ground truth
-- and what the route, the PDF fetch and every external source use. The
-- structured fields below are GENERATED from it, so they can never drift and
-- there is nothing extra for the client to send.
--   '0625_s25_22'  ->  subject 0625, series s, 2025, paper 2, variant 2
-- --------------------------------------------------------------------------
create table if not exists exam_attempts (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,

  paper_id        text not null
                    check (paper_id ~ '^[0-9]{4}_[msw][0-9]{2}_[0-9]{1,2}$'),

  subject_code    text
                    generated always as (split_part(paper_id, '_', 1)) stored,
  series          text
                    generated always as (left(split_part(paper_id, '_', 2), 1)) stored,
  exam_year       smallint
                    generated always as (
                      (2000 + substr(split_part(paper_id, '_', 2), 2, 2)::int)::smallint
                    ) stored,
  paper_number    smallint
                    generated always as (
                      nullif(left(split_part(paper_id, '_', 3), 1), '')::smallint
                    ) stored,
  variant         smallint
                    generated always as (
                      case when length(split_part(paper_id, '_', 3)) >= 2
                           then substr(split_part(paper_id, '_', 3), 2, 1)::smallint
                      end
                    ) stored,

  status          attempt_status not null default 'in_progress',
  started_at      timestamptz not null default now(),
  finished_at     timestamptz,
  duration_ms     integer check (duration_ms >= 0),   -- milliseconds, genuinely

  questions_total    smallint,                        -- from the answer key
  questions_answered smallint not null default 0,

  client_timezone text not null default 'UTC',
  -- Written by the client at insert. NOT generated: `at time zone <column>` is
  -- STABLE, not IMMUTABLE, so Postgres rejects it in a generated expression.
  local_date      date not null,

  metrics_version smallint not null default 1,
  created_at      timestamptz not null default now()
);

create index if not exists idx_ea_user_started  on exam_attempts(user_id, started_at desc);
create index if not exists idx_ea_user_subject  on exam_attempts(user_id, subject_code);
create index if not exists idx_ea_user_date     on exam_attempts(user_id, local_date);
create index if not exists idx_ea_user_status   on exam_attempts(user_id, status);
create index if not exists idx_ea_paper         on exam_attempts(paper_id);

-- --------------------------------------------------------------------------
-- Per-question facts: what the student actually did.
-- Deterministic - recomputing them from the same events always gives the same
-- answer. Weighted composites live in question_metrics instead.
-- --------------------------------------------------------------------------
create table if not exists question_attempts (
  id              uuid primary key default gen_random_uuid(),
  exam_attempt_id uuid not null references exam_attempts(id) on delete cascade,
  question_number smallint not null,

  selected_option smallint check (selected_option >= 0),  -- null = unanswered
  eliminated_mask smallint not null default 0,            -- bit i set = option i ruled out

  -- Authoritative. Set by trigger from paper_answers; never trusted from the client.
  is_correct      boolean,

  time_spent_ms   integer not null default 0 check (time_spent_ms >= 0),
  hesitation_ms   integer check (hesitation_ms >= 0),

  option_switch_count        smallint not null default 0,
  elimination_reversal_count smallint not null default 0,
  revisit_count              smallint not null default 0,

  -- Real counts now (were previously coerced to 0/1 at the write site).
  marked_for_review_count   smallint not null default 0,
  marked_as_difficult_count smallint not null default 0,
  marked_for_save_count     smallint not null default 0,

  stable_elimination_ratio real not null default 0
      check (stable_elimination_ratio between 0 and 1),
  exploration_depth   smallint not null default 0,
  exploration_breadth smallint not null default 0,

  created_at timestamptz not null default now(),
  unique (exam_attempt_id, question_number)
);

create index if not exists idx_qa_attempt on question_attempts(exam_attempt_id);
create index if not exists idx_qa_correct on question_attempts(exam_attempt_id, is_correct);

-- --------------------------------------------------------------------------
-- Server-side marking. Closes both "correctness is never stored" and
-- "correctness is whatever the browser claims".
-- --------------------------------------------------------------------------
create or replace function set_question_correctness() returns trigger
language plpgsql as $$
declare
  key_option smallint;
begin
  if new.selected_option is null then
    new.is_correct := null;
    return new;
  end if;

  select pa.correct_option into key_option
  from paper_answers pa
  join exam_attempts ea on ea.paper_id = pa.paper_id
  where ea.id = new.exam_attempt_id
    and pa.question_number = new.question_number;

  -- No cached key yet: leave null rather than guess. Re-running the update
  -- once the key is cached will fill it in.
  new.is_correct := case when key_option is null then null
                         else key_option = new.selected_option end;
  return new;
end $$;

drop trigger if exists trg_question_correctness on question_attempts;
create trigger trg_question_correctness
  before insert or update of selected_option, question_number
  on question_attempts
  for each row execute function set_question_correctness();

-- Re-mark an attempt after its answer key arrives (or is corrected).
create or replace function remark_attempt(p_attempt_id uuid) returns integer
language sql as $$
  with touched as (
    update question_attempts
       set selected_option = selected_option   -- fires the trigger
     where exam_attempt_id = p_attempt_id
    returning 1
  ) select count(*)::integer from touched;
$$;

-- --------------------------------------------------------------------------
-- Weighted composites, versioned.
-- Separate from question_attempts because these depend on tunable weights AND
-- on cross-question normalisation (meanTime/meanNorm/stdNorm across the whole
-- paper) - so they are not properties of a single response, and they change
-- when the formula changes.
-- --------------------------------------------------------------------------
create table if not exists metrics_versions (
  version     smallint primary key,
  description text not null,
  weights     jsonb not null,
  created_at  timestamptz not null default now()
);

insert into metrics_versions (version, description, weights) values (
  1,
  'Initial weights, as hardcoded in src/lib/processing/enrichAnalytics.ts',
  '{
     "confidence": {"markReview":0.4, "stableElimination":0.3, "time":0.2, "revisit":0.1},
     "difficulty": {"markDifficult":0.4, "optionSwitch":0.25, "inverseConfidence":0.2,
                    "hesitation":0.1, "revisit":0.05},
     "interest":   {"markSave":0.35, "highlightActivity":0.25, "revisit":0.15,
                    "markReview":0.05, "difficulty":0.05, "time":0.15}
   }'::jsonb
) on conflict (version) do nothing;

create table if not exists question_metrics (
  question_attempt_id uuid not null references question_attempts(id) on delete cascade,
  metrics_version     smallint not null references metrics_versions(version),
  confidence real not null check (confidence between 0 and 1),
  difficulty real not null check (difficulty between 0 and 1),
  interest   real not null check (interest   between 0 and 1),
  computed_at timestamptz not null default now(),
  primary key (question_attempt_id, metrics_version)
);

-- --------------------------------------------------------------------------
-- Raw interaction stream. Previously discarded at the end of every attempt.
-- ~200 rows per paper; this is what makes metric retuning recoverable and
-- powers answer-change / pacing analysis that aggregates cannot express.
-- --------------------------------------------------------------------------
create table if not exists attempt_events (
  id              bigserial primary key,
  exam_attempt_id uuid not null references exam_attempts(id) on delete cascade,
  seq             integer not null,          -- client ordinal; breaks timestamp ties
  question_number smallint,
  element_type    text not null,             -- 'highlight' | 'focusArea' | 'Copy' | 'Flag' | 'Star' | 'Save'
  -- Left as text, not an enum: the vocabulary in src/lib/utils/utilsTypes.ts is
  -- still churning and an enum makes every addition a migration.
  action_type     text not null,             -- 'setCorrect' | 'correctToElim' | 'userClick' | ...
  option_index    smallint,
  elapsed_ms      integer not null check (elapsed_ms >= 0),  -- ms since exam start
  occurred_at     timestamptz not null,
  unique (exam_attempt_id, seq)
);

create index if not exists idx_ev_attempt   on attempt_events(exam_attempt_id);
create index if not exists idx_ev_question  on attempt_events(exam_attempt_id, question_number);
create index if not exists idx_ev_element   on attempt_events(exam_attempt_id, element_type);

-- --------------------------------------------------------------------------
-- Goals (statistic #14, "Next Goal")
-- --------------------------------------------------------------------------
do $$ begin
  create type goal_kind as enum ('papers_per_week','accuracy_target','subject_focus','streak_days');
exception when duplicate_object then null; end $$;

create table if not exists goals (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  kind         goal_kind not null,
  subject_code text references subjects(code),   -- null = all subjects
  target       numeric not null,
  active       boolean not null default true,
  created_at   timestamptz not null default now()
);

create index if not exists idx_goals_user on goals(user_id) where active;

-- ==========================================================================
-- Read layer
-- ==========================================================================

create or replace view v_attempt_summary as
select
  ea.id, ea.user_id, ea.paper_id, ea.status,
  ea.subject_code, s.name as subject_name, s.qualification,
  ea.series, ea.exam_year, ea.paper_number, ea.variant,
  ea.started_at, ea.finished_at, ea.duration_ms, ea.local_date, ea.client_timezone,
  ea.questions_total,
  count(qa.id)                                         as questions_recorded,
  count(qa.selected_option)                            as questions_answered,
  count(*) filter (where qa.is_correct)                as questions_correct,
  avg((qa.is_correct)::int)                            as accuracy,
  avg(qa.time_spent_ms)::int                           as avg_time_per_question_ms
from exam_attempts ea
left join subjects s          on s.code = ea.subject_code
left join question_attempts qa on qa.exam_attempt_id = ea.id
group by ea.id, s.name, s.qualification;

-- Per-question flags. This is where "overconfident", "underconfident" and
-- "guessed" actually get decided - none of them existed before, and none of
-- them CAN be decided without is_correct.
create or replace view v_question_flags as
with per_attempt as (
  select exam_attempt_id,
         percentile_cont(0.5) within group (order by time_spent_ms) as median_time_ms
  from question_attempts
  group by exam_attempt_id
)
select
  qa.id as question_attempt_id,
  qa.exam_attempt_id,
  qa.question_number,
  qa.is_correct,
  qm.confidence,
  qa.time_spent_ms,
  pa.median_time_ms,
  -- Fast, no eliminations, essentially no interaction: a guess rather than a
  -- decision. Correct guesses inflate accuracy and hide real gaps, so they are
  -- surfaced separately.
  (qa.time_spent_ms < 0.4 * pa.median_time_ms
     and qa.exploration_depth <= 1
     and qa.eliminated_mask = 0)                       as is_guess,
  (qm.confidence >= 0.7 and qa.is_correct is false)    as is_overconfident,
  (qm.confidence <= 0.4 and qa.is_correct is true)     as is_underconfident
from question_attempts qa
join exam_attempts ea on ea.id = qa.exam_attempt_id
join per_attempt   pa on pa.exam_attempt_id = qa.exam_attempt_id
left join question_metrics qm
       on qm.question_attempt_id = qa.id
      and qm.metrics_version = ea.metrics_version;

-- Calibration curve: predicted confidence vs observed accuracy, by decile.
-- A perfectly calibrated student sits on the diagonal.
create or replace view v_calibration_curve as
select
  ea.user_id,
  width_bucket(qm.confidence, 0, 1, 10)      as confidence_bucket,
  count(*)                                   as questions,
  avg(qm.confidence)                         as mean_confidence,
  avg((qa.is_correct)::int)                  as observed_accuracy,
  avg((qa.is_correct)::int) - avg(qm.confidence) as calibration_gap
from question_attempts qa
join exam_attempts ea      on ea.id = qa.exam_attempt_id
join question_metrics qm   on qm.question_attempt_id = qa.id
                          and qm.metrics_version = ea.metrics_version
where qa.is_correct is not null
group by ea.user_id, width_bucket(qm.confidence, 0, 1, 10);

create or replace view v_daily_activity as
select
  ea.user_id,
  ea.local_date,
  count(distinct ea.id)                 as papers,
  sum(ea.duration_ms)                   as total_time_ms,
  count(qa.id)                          as questions,
  count(*) filter (where qa.is_correct) as correct
from exam_attempts ea
left join question_attempts qa on qa.exam_attempt_id = ea.id
where ea.status = 'completed'
group by ea.user_id, ea.local_date;

-- "Peak solving hour" - local, per D10. Kept separate from v_daily_activity
-- because it aggregates over attempts rather than over days.
create or replace view v_hour_of_day as
select
  ea.user_id,
  extract(hour from ea.started_at at time zone ea.client_timezone)::smallint as local_hour,
  count(*)             as papers,
  sum(ea.duration_ms)  as total_time_ms
from exam_attempts ea
where ea.status = 'completed'
group by ea.user_id, 2;

create or replace view v_subject_stats as
select
  ea.user_id,
  ea.subject_code,
  s.name as subject_name,
  count(distinct ea.id)                 as attempts,
  avg((qa.is_correct)::int)             as accuracy,
  sum(ea.duration_ms)                   as total_time_ms,
  max(ea.finished_at)                   as last_attempt_at,
  avg(qm.confidence)                    as avg_confidence,
  avg(qm.difficulty)                    as avg_difficulty,
  avg(qm.interest)                      as avg_interest
from exam_attempts ea
left join subjects s           on s.code = ea.subject_code
left join question_attempts qa on qa.exam_attempt_id = ea.id
left join question_metrics qm  on qm.question_attempt_id = qa.id
                              and qm.metrics_version = ea.metrics_version
where ea.status = 'completed'
group by ea.user_id, ea.subject_code, s.name;

-- Per-topic mastery. Returns nothing until `topics` and
-- `paper_answers.topic_id` are populated - see src/constants/topicMap.ts.
create or replace view v_topic_mastery as
select
  ea.user_id,
  t.subject_code,
  t.id   as topic_id,
  t.name as topic_name,
  count(*)                              as questions,
  count(*) filter (where qa.is_correct) as correct,
  avg((qa.is_correct)::int)             as accuracy,
  avg(qa.time_spent_ms)::int            as avg_time_ms
from question_attempts qa
join exam_attempts ea on ea.id = qa.exam_attempt_id
join paper_answers pa on pa.paper_id = ea.paper_id
                     and pa.question_number = qa.question_number
join topics t         on t.id = pa.topic_id
where ea.status = 'completed'
group by ea.user_id, t.subject_code, t.id, t.name;

-- --------------------------------------------------------------------------
-- Drop the table that nothing ever referenced.
-- --------------------------------------------------------------------------
drop table if exists attempts;
