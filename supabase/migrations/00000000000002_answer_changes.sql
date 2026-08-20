-- ==========================================================================
--
-- Answer-change quality: when you changed your mind, were you right to?
--
-- This was the highest-value unbuilt metric in docs/roadmap.md B6. The raw
-- material has been recorded since `attempt_events` existed - every option
-- transition, with the option index and its sequence number - but nothing read
-- it. `question_attempts.option_switch_count` only ever counted switches, never
-- whether they helped, which is the part a student can act on.
--
-- The two events that ESTABLISH a choice are 'setCorrect' (picked from
-- nothing) and 'elimToCorrect' (promoted an option previously ruled out).
-- 'deselectedCorrect' and 'correctToElim' clear a choice; they are not changes
-- of answer on their own, because the next 'setCorrect' is what names the new
-- one. Ordering is by `seq`, not by timestamp: two events inside the same
-- millisecond are common and `seq` is the field that is actually total.
-- ==========================================================================

create or replace view v_answer_changes as
with choices as (
  -- Every moment an option became the chosen answer, in order.
  select
    ae.exam_attempt_id,
    ae.question_number,
    ae.seq,
    ae.option_index,
    ae.elapsed_ms
  from attempt_events ae
  where ae.element_type = 'highlight'
    and ae.action_type in ('setCorrect', 'elimToCorrect')
    and ae.option_index is not null
    and ae.question_number is not null
),
transitions as (
  -- Consecutive pairs on the same question. A pair whose option differs is an
  -- answer change; re-selecting the same option is not.
  select
    c.exam_attempt_id,
    c.question_number,
    lag(c.option_index) over w  as from_option,
    c.option_index              as to_option,
    c.elapsed_ms
  from choices c
  window w as (partition by c.exam_attempt_id, c.question_number order by c.seq)
)
select
  ea.user_id,
  ea.id            as exam_attempt_id,
  ea.paper_id,
  ea.subject_code,
  ea.local_date,
  t.question_number,
  t.from_option,
  t.to_option,
  t.elapsed_ms,
  (t.from_option = pa.correct_option) as was_right,
  (t.to_option   = pa.correct_option) as is_right,
  case
    when t.from_option = pa.correct_option and t.to_option <> pa.correct_option then 'right_to_wrong'
    when t.from_option <> pa.correct_option and t.to_option = pa.correct_option then 'wrong_to_right'
    else 'wrong_to_wrong'
  end as verdict
from transitions t
join exam_attempts ea on ea.id = t.exam_attempt_id
join paper_answers pa on pa.paper_id = ea.paper_id
                     and pa.question_number = t.question_number
where t.from_option is not null
  and t.from_option <> t.to_option;

alter view v_answer_changes set (security_invoker = true);
grant select on v_answer_changes to authenticated;

-- --------------------------------------------------------------------------
-- The per-user roll-up the stats page reads. Aggregating here rather than in
-- the client keeps it one row over the wire instead of one per change, and
-- means the same definition backs any future consumer.
-- --------------------------------------------------------------------------
create or replace view v_answer_change_summary as
select
  user_id,
  count(*)                                             as changes,
  count(*) filter (where verdict = 'wrong_to_right')    as wrong_to_right,
  count(*) filter (where verdict = 'right_to_wrong')    as right_to_wrong,
  count(*) filter (where verdict = 'wrong_to_wrong')    as wrong_to_wrong,
  -- Net marks the changing gained or cost. This is the number worth acting on:
  -- positive means trusting a second look pays, negative means first instinct
  -- was better.
  count(*) filter (where verdict = 'wrong_to_right')
    - count(*) filter (where verdict = 'right_to_wrong') as net_marks
from v_answer_changes
group by user_id;

alter view v_answer_change_summary set (security_invoker = true);
grant select on v_answer_change_summary to authenticated;
