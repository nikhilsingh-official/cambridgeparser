-- ==========================================================================
--
-- The IDE's attempt history, and the stats that can only be built on top of
-- one.
--
-- WHY THIS EXISTS. record_ide_attempt() upserts into ide_progress, so a 3/6
-- followed by a 6/6 leaves a single row reading 6/6 and no evidence that the
-- 3/6 ever happened. Every aggregate the solver's stats page is built from -
-- accuracy over time, the practice streak, "am I improving" - is a function of
-- ORDERED attempts, and none of them can be recovered from a best-score
-- upsert. docs/roadmap.md A4 states the consequence plainly: that history is
-- unrecoverable for every submission made before this table exists. This
-- migration therefore lands BEFORE anything starts calling the function, not
-- after.
--
-- WHY IT IS NOT A REUSE OF exam_attempts. A pseudocode submission is graded
-- against a rubric of marking points, not against one right answer out of
-- four. It has no option_count, no chance level, and its unit of credit is a
-- marking point rather than a question. Per docs/solver/future_work.md SS6.2
-- it is a SIBLING of the solver's attempt log, sharing the conventions
-- (user_id, local_date, client_timezone) that let the two be read on one
-- timeline - not a row squeezed into a table that means something else.
-- ==========================================================================

-- --------------------------------------------------------------------------
-- One row per graded submission. Never updated, never deleted.
--
-- APPEND-ONLY IS ENFORCED, NOT DOCUMENTED. There is a select policy and an
-- insert policy below and deliberately no update or delete policy, and the
-- grants are select+insert only. A student cannot revise or erase a past
-- submission through the API even if a future client tries to, which is what
-- makes this table usable as evidence rather than as a cache.
-- --------------------------------------------------------------------------
create table if not exists public.ide_attempts (
  id          bigserial primary key,
  user_id     uuid not null references auth.users (id) on delete cascade,
  -- text, and not a foreign key, for the same reason as ide_progress.record_id:
  -- the corpus pipeline renumbers records between builds and owns that id.
  record_id   text    not null,
  score       integer not null check (score >= 0),
  max_marks   integer not null check (max_marks >= 0),
  -- 'pseudocode' | 'fill_blank_sheet'. Left as text rather than an enum
  -- because the IDE is still growing answer kinds and an enum makes each one a
  -- migration - same call as attempt_events.element_type.
  answer_kind text,
  -- What the student actually submitted. The single genuinely unrecoverable
  -- artifact here: a score can be recomputed from a rubric, an answer cannot
  -- be recovered from a score.
  source      text,
  -- The per-marking-point awards from grading-result/v1. jsonb rather than a
  -- child table because nothing yet queries INSIDE a marking point; when
  -- something does, this is lossless enough to normalise from.
  points      jsonb,
  -- The student's own calendar day, not UTC. A streak is a local-calendar
  -- idea; see the note on exam_attempts.local_date in the solver schema.
  local_date      date not null,
  client_timezone text,
  created_at      timestamptz not null default now()
);

alter table public.ide_attempts enable row level security;

create policy ide_attempts_select_own on public.ide_attempts
  for select using (auth.uid() = user_id);
create policy ide_attempts_insert_own on public.ide_attempts
  for insert with check (auth.uid() = user_id);
-- No update policy and no delete policy. See the header.

create index if not exists idx_ide_att_user_date
  on public.ide_attempts (user_id, local_date);
create index if not exists idx_ide_att_user_record
  on public.ide_attempts (user_id, record_id, created_at);

-- --------------------------------------------------------------------------
-- record_ide_attempt, second edition: append THEN upsert.
--
-- The old four-argument version is dropped rather than overloaded. It had zero
-- callers (verified with `grep -rn record_ide_attempt src/`), and leaving an
-- overload in place would let a caller reach the version that keeps no
-- history without knowing it had done so.
--
-- Both writes are in one function and therefore in one transaction: there is
-- no state in which a submission is counted in the progress row but missing
-- from the log, which is the failure mode that would quietly corrupt every
-- trend built on this table.
-- --------------------------------------------------------------------------
drop function if exists public.record_ide_attempt(text, integer, integer, text);

create or replace function public.record_ide_attempt(
  p_record_id       text,
  p_score           integer,
  p_max_marks       integer,
  p_source          text    default null,
  p_answer_kind     text    default null,
  p_points          jsonb   default null,
  p_client_timezone text    default null
) returns public.ide_progress
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_user_id uuid    := auth.uid();
  v_solved  boolean := p_max_marks > 0 and p_score >= p_max_marks;
  v_score   integer := greatest(coalesce(p_score, 0), 0);
  v_tz      text;
  v_row     public.ide_progress;
begin
  if v_user_id is null then
    raise exception 'record_ide_attempt requires an authenticated caller'
      using errcode = '28000';
  end if;

  -- The timezone arrives from the client, so it is checked against the
  -- server's own catalogue before being used. An unknown name would otherwise
  -- raise inside `at time zone` and fail the whole submission over a cosmetic
  -- field; UTC is the safe fallback because the worst case is one submission
  -- filed against the wrong calendar day.
  select p_client_timezone into v_tz
    from pg_timezone_names where name = p_client_timezone;
  v_tz := coalesce(v_tz, 'UTC');

  -- The log first. If this fails the whole call fails and the progress row is
  -- not advanced either, which is the correct direction to fail in: a lost
  -- submission is recoverable by re-submitting, a progress row with no
  -- corresponding history is not.
  insert into public.ide_attempts
    (user_id, record_id, score, max_marks, answer_kind, source, points,
     local_date, client_timezone)
  values
    (v_user_id, p_record_id, v_score, greatest(coalesce(p_max_marks, 0), 0),
     p_answer_kind, p_source, p_points,
     (now() at time zone v_tz)::date, p_client_timezone);

  insert into public.ide_progress as p
    (user_id, record_id, status, best_score, max_marks, attempts, last_source, updated_at)
  values
    (v_user_id, p_record_id,
     case when v_solved then 'solved' else 'attempted' end,
     v_score, p_max_marks, 1, p_source, now())
  on conflict (user_id, record_id) do update set
    -- 'solved' is absorbing: a later low score cannot un-solve a question.
    status      = case when v_solved or p.status = 'solved' then 'solved' else 'attempted' end,
    best_score  = greatest(p.best_score, excluded.best_score),
    max_marks   = excluded.max_marks,
    attempts    = p.attempts + 1,
    last_source = coalesce(excluded.last_source, p.last_source),
    updated_at  = now()
  returning * into v_row;

  return v_row;
end;
$$;

-- --------------------------------------------------------------------------
-- v_ide_stats, widened.
--
-- It kept two counters, which was everything the RTDB `stats/` subtree held.
-- The four added below are what a stats tile actually needs: how much work,
-- how much credit, and when it last happened.
--
-- Still one view over ONE table, so no column here can disagree with another.
-- security_invoker is repeated because `create or replace view` does not
-- inherit the old view's options - dropping it here would silently reopen the
-- RLS bypass this view was fixed for once already (docs/roadmap.md A1).
-- --------------------------------------------------------------------------
create or replace view public.v_ide_stats
  with (security_invoker = true) as
select
  user_id,
  count(*) filter (where status in ('attempted', 'solved')) as attempted,
  count(*) filter (where status = 'solved')                 as solved,
  -- Submissions, not questions: someone who solved one question on the fourth
  -- try did four times the work of someone who solved it first time.
  coalesce(sum(attempts), 0)                                as submissions,
  coalesce(sum(best_score), 0)                              as best_marks,
  coalesce(sum(max_marks) filter (where attempts > 0), 0)   as best_marks_possible,
  max(updated_at)                                           as last_attempt_at
from public.ide_progress
group by user_id;

-- --------------------------------------------------------------------------
-- v_ide_daily: the sibling of v_daily_activity, over the log rather than over
-- the progress rows - a streak is made of days you worked, and the progress
-- table only remembers the last one.
--
-- Column names deliberately match v_daily_activity where they mean the same
-- thing (user_id, local_date), so the two can be merged on one timeline
-- without a translation layer.
-- --------------------------------------------------------------------------
create or replace view public.v_ide_daily
  with (security_invoker = true) as
select
  user_id,
  local_date,
  count(*)                                                  as submissions,
  count(distinct record_id)                                 as questions,
  count(*) filter (where max_marks > 0 and score >= max_marks) as solved_submissions,
  coalesce(sum(score), 0)                                   as marks_awarded,
  coalesce(sum(max_marks), 0)                               as marks_possible
from public.ide_attempts
group by user_id, local_date;

-- --------------------------------------------------------------------------
-- Privileges. RLS says which rows; these say whether the table may be touched
-- at all. Both are required - see the note in 00000000000001_ide_schema.sql.
--
-- INSERT but no UPDATE and no DELETE: the append-only rule again, at the
-- second of the two gates it has to pass.
-- --------------------------------------------------------------------------
grant select, insert on public.ide_attempts to authenticated;
grant usage, select on sequence public.ide_attempts_id_seq to authenticated;
grant select on public.v_ide_stats to authenticated;
grant select on public.v_ide_daily to authenticated;

revoke all on function
  public.record_ide_attempt(text, integer, integer, text, text, jsonb, text) from public;
grant execute on function
  public.record_ide_attempt(text, integer, integer, text, text, jsonb, text) to authenticated;
