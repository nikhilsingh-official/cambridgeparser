-- ==========================================================================
--
-- Moves the three behavioural-flag thresholds out of the database.
--
-- WHY. v_question_flags decided, in SQL, that confidence >= 0.7 on a wrong
-- answer is overconfidence, that <= 0.4 on a right one is underconfidence, and
-- that under 0.4x the median time with no eliminations is a guess. Every OTHER
-- number that constitutes a claim about a student lives in
-- src/lib/stats/model.ts, deliberately and for one reason: so there is exactly
-- one place a claim can be read, checked and changed.
--
-- These three were the exception, and it was the expensive kind. docs/roadmap.md
-- B6 records that all three were "picked, not measured" and must be checked
-- against real data once a few hundred questions exist - and while they lived
-- here, checking one meant writing a migration, and comparing two settings was
-- impossible. In model.ts they are constants beside the flags they belong with.
--
-- WHAT CHANGES. The view stops deciding and starts REPORTING: the two columns
-- the guess rule needs (exploration_depth, eliminated_mask) are exposed, and
-- the three boolean columns are dropped. Dropped rather than left in place on
-- purpose - two implementations of "what is a guess" is precisely the drift
-- this migration exists to end. summariseFlags() in
-- src/lib/supabase/queries/focus.ts is the only consumer they ever had.
--
-- `create or replace view` cannot remove a column, so the view is dropped and
-- rebuilt. That loses security_invoker and the grant, both of which are
-- restored at the bottom - the first is not the default, and without it the
-- view reads question_attempts as its owner and RLS never applies.
-- ==========================================================================

drop view if exists v_question_flags;

create view v_question_flags as
with per_attempt as (
  select
    qa.exam_attempt_id,
    percentile_cont(0.5) within group (order by qa.time_spent_ms) as median_time_ms
  from question_attempts qa
  group by qa.exam_attempt_id
)
select
  qa.id as question_attempt_id,
  qa.exam_attempt_id,
  ea.user_id,
  ea.paper_id,
  ea.subject_code,
  ea.local_date,
  qa.question_number,
  qa.is_correct,
  qm.confidence,
  qa.time_spent_ms,
  qa.hesitation_ms,
  pa.median_time_ms,
  -- the two inputs to the guess rule, which the previous version consumed
  -- internally and never exposed. Without them the rule cannot be evaluated
  -- anywhere but here, which is what forced the threshold to live here too.
  qa.exploration_depth,
  qa.eliminated_mask
from question_attempts qa
join exam_attempts ea on ea.id = qa.exam_attempt_id
join per_attempt   pa on pa.exam_attempt_id = qa.exam_attempt_id
left join question_metrics qm
       on qm.question_attempt_id = qa.id
      and qm.metrics_version = ea.metrics_version;

-- Not the default, and the whole of this view's row-level security depends on
-- it - see the note in 00000000000000_solver_schema.sql.
alter view v_question_flags set (security_invoker = true);
grant select on v_question_flags to authenticated;
