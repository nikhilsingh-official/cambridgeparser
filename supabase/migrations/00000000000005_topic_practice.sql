-- ==========================================================================
--
-- The per-question practice sequence, per topic. Everything the metric model
-- in src/lib/stats/model.ts needs that an aggregate cannot give it.
--
-- WHY A SEQUENCE AND NOT MORE AGGREGATES
-- v_topic_mastery answers "how good am I at this topic" with a ratio. Three of
-- the five metrics being built need something a ratio cannot carry:
--
--   1. Bayesian Knowledge Tracing (Corbett & Anderson 1995) is a recurrence
--      over ORDERED outcomes. 8/10 tells you nothing about whether the two
--      misses were the first two attempts or the last two, and those are
--      opposite conclusions.
--   2. The forgetting curve (Ebbinghaus 1885; Settles & Meeder 2016 eq. 1)
--      needs the lag since the topic was last practised.
--   3. The wrong-answer set needs to name the actual questions, which means
--      paper_id and question_number, not a count of them.
--
-- One view serves all three rather than three views over the same join.
--
-- GRAIN: one row per (question attempt x topic). A question tagged with two
-- topics appears twice, deliberately - it is evidence about both. Do not sum
-- marks across this view to get a paper total; see the header of
-- 00000000000004_question_topics.sql for why.
-- ==========================================================================

create or replace view v_topic_practice as
select
  ea.user_id,
  t.id           as topic_id,
  t.subject_code,
  t.name         as topic_name,
  ea.id          as exam_attempt_id,
  ea.paper_id,
  -- Generated from paper_id by exam_attempts. Carried here because grade
  -- thresholds are per COMPONENT: IGCSE Paper 1 is Core and caps at grade C,
  -- Paper 2 is Extended and does not, so a threshold applied without knowing
  -- which paper a question came from is applied to the wrong scale.
  ea.paper_number,
  qa.question_number,
  qa.is_correct,
  qa.time_spent_ms,
  -- Chance level is a STRUCTURAL fact for a multiple-choice question, not a
  -- fitted parameter: with four options an unknowing student is right 1/4 of
  -- the time. This is what lets the model use a knowledge-tracing guess
  -- parameter it did not have to invent. See model.ts SS B.
  pa.option_count,
  pa.marks,
  -- started_at, not finished_at: the order questions were MET in. Both are
  -- carried because the decay model measures lag in whole local days while the
  -- knowledge-tracing recurrence only needs a stable total order.
  ea.started_at,
  ea.local_date
from question_attempts qa
join exam_attempts ea   on ea.id = qa.exam_attempt_id
join paper_answers pa   on pa.paper_id = ea.paper_id
                       and pa.question_number = qa.question_number
join question_topics qt on qt.paper_id = ea.paper_id
                       and qt.question_number = qa.question_number
join topics t           on t.id = qt.topic_id
where ea.status = 'completed'
  -- An unanswered question is not evidence of anything. Knowledge tracing
  -- treats every observation as a Bernoulli trial, and a null is not one.
  and qa.is_correct is not null;

-- security_invoker is NOT the default. Without it this view reads its base
-- tables as the view owner and RLS never applies - which on a view keyed by
-- user_id would hand every student everybody else's practice history.
alter view v_topic_practice set (security_invoker = true);
grant select on v_topic_practice to authenticated;

-- --------------------------------------------------------------------------
-- v_topic_mastery gains the two dates the decay model needs. Recreated in
-- full because `create or replace view` cannot add a column in the middle,
-- and the column order below is the existing one plus two at the end.
-- --------------------------------------------------------------------------
create or replace view v_topic_mastery as
select
  ea.user_id,
  t.subject_code,
  t.id   as topic_id,
  t.name as topic_name,
  count(*)                              as questions,
  count(*) filter (where qa.is_correct) as correct,
  coalesce(sum(pa.marks) filter (where qa.is_correct), 0)::int      as marks_awarded,
  coalesce(sum(pa.marks), 0)::int                                   as marks_total,
  coalesce(sum(pa.marks) filter (where qa.is_correct), 0)::numeric
    / nullif(sum(pa.marks), 0)          as accuracy,
  avg(qa.time_spent_ms)::int            as avg_time_ms,
  -- the lag term of the forgetting curve. Local dates rather than
  -- timestamps because "days since" is what the model measures in, and
  -- local_date is already the student's own calendar day.
  min(ea.local_date)                    as first_practised_on,
  max(ea.local_date)                    as last_practised_on,
  -- Modal option count, for the chance level. A topic's questions could in
  -- principle mix 4- and 5-option papers; the mode is the honest single
  -- answer and the per-question truth stays available in v_topic_practice.
  mode() within group (order by pa.option_count) as option_count
from question_attempts qa
join exam_attempts ea   on ea.id = qa.exam_attempt_id
join paper_answers pa   on pa.paper_id = ea.paper_id
                       and pa.question_number = qa.question_number
join question_topics qt on qt.paper_id = ea.paper_id
                       and qt.question_number = qa.question_number
join topics t           on t.id = qt.topic_id
where ea.status = 'completed'
group by ea.user_id, t.subject_code, t.id, t.name;

alter view v_topic_mastery set (security_invoker = true);
grant select on v_topic_mastery to authenticated;
