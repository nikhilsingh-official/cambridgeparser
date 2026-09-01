-- ==========================================================================
--
-- Proves the policies in 00000000000003_solver_rls.sql actually isolate users.
-- A policy that exists is not a policy that works: the failure mode of RLS is
-- silent (you see rows you should not, or none at all), so it has to be
-- exercised rather than reviewed.
--
-- Run:  docker exec -i supabase_db_cambridgeparser psql -U postgres -d postgres \
--         -v ON_ERROR_STOP=1 < tests/test_solver_rls.sql
--
-- Runs in a transaction and rolls back; it writes nothing that survives.
-- ==========================================================================

begin;

do $$
declare
  v_owner    uuid;
  v_intruder uuid := '00000000-0000-4000-8000-0000deadbeef';
  v_attempt  uuid;
  v_n        bigint;
  v_failed   boolean;
begin
  -- The seeded user, whose data everything below tries to reach.
  select user_id into v_owner from public.exam_attempts limit 1;
  if v_owner is null then
    raise exception 'no seeded attempts - run `npx supabase db reset` first';
  end if;
  select id into v_attempt from public.exam_attempts where user_id = v_owner limit 1;

  -- ---------------------------------------------------------------- owner
  set local role authenticated;
  perform set_config('request.jwt.claims',
                     json_build_object('sub', v_owner, 'role', 'authenticated')::text,
                     true);

  select count(*) into v_n from public.exam_attempts;
  if v_n = 0 then raise exception 'owner cannot see their own attempts (% rows)', v_n; end if;
  raise notice 'owner sees % exam_attempts', v_n;

  select count(*) into v_n from public.question_attempts;
  if v_n = 0 then raise exception 'owner cannot see their own question_attempts'; end if;
  raise notice 'owner sees % question_attempts', v_n;

  select count(*) into v_n from public.attempt_events;
  if v_n = 0 then raise exception 'owner cannot see their own attempt_events'; end if;
  raise notice 'owner sees % attempt_events', v_n;

  select count(*) into v_n from public.question_metrics;
  if v_n = 0 then raise exception 'owner cannot see their own question_metrics'; end if;
  raise notice 'owner sees % question_metrics', v_n;

  select count(*) into v_n from public.v_attempt_summary;
  if v_n = 0 then raise exception 'owner cannot read v_attempt_summary'; end if;
  raise notice 'owner sees % rows in v_attempt_summary', v_n;

  select count(*) into v_n from public.v_question_flags;
  if v_n = 0 then raise exception 'owner cannot read v_question_flags'; end if;
  raise notice 'owner sees % rows in v_question_flags', v_n;

  select count(*) into v_n from public.v_topic_mastery;
  if v_n = 0 then raise exception 'v_topic_mastery returned 0 rows for the owner'; end if;
  raise notice 'owner sees % rows in v_topic_mastery', v_n;

  select count(*) into v_n from public.v_topic_practice;
  if v_n = 0 then raise exception 'v_topic_practice returned 0 rows for the owner'; end if;
  raise notice 'owner sees % rows in v_topic_practice', v_n;

  -- ------------------------------------------------------------- intruder
  reset role;
  set local role authenticated;
  perform set_config('request.jwt.claims',
                     json_build_object('sub', v_intruder, 'role', 'authenticated')::text,
                     true);

  select count(*) into v_n from public.exam_attempts;
  if v_n <> 0 then raise exception 'LEAK: intruder sees % exam_attempts', v_n; end if;

  select count(*) into v_n from public.question_attempts;
  if v_n <> 0 then raise exception 'LEAK: intruder sees % question_attempts', v_n; end if;

  select count(*) into v_n from public.attempt_events;
  if v_n <> 0 then raise exception 'LEAK: intruder sees % attempt_events', v_n; end if;

  select count(*) into v_n from public.question_metrics;
  if v_n <> 0 then raise exception 'LEAK: intruder sees % question_metrics', v_n; end if;

  select count(*) into v_n from public.goals;
  if v_n <> 0 then raise exception 'LEAK: intruder sees % goals', v_n; end if;

  -- The views are the subtler risk: security_invoker is NOT the default, and
  -- without it a view reads its base table as postgres and RLS never applies.
  select count(*) into v_n from public.v_attempt_summary;
  if v_n <> 0 then raise exception 'LEAK via view: intruder sees % rows in v_attempt_summary', v_n; end if;

  select count(*) into v_n from public.v_question_flags;
  if v_n <> 0 then raise exception 'LEAK via view: intruder sees % rows in v_question_flags', v_n; end if;

  select count(*) into v_n from public.v_subject_stats;
  if v_n <> 0 then raise exception 'LEAK via view: intruder sees % rows in v_subject_stats', v_n; end if;

  select count(*) into v_n from public.v_daily_activity;
  if v_n <> 0 then raise exception 'LEAK via view: intruder sees % rows in v_daily_activity', v_n; end if;

  select count(*) into v_n from public.v_answer_change_summary;
  if v_n <> 0 then raise exception 'LEAK via view: intruder sees % rows in v_answer_change_summary', v_n; end if;

  -- v_topic_mastery joins reference data (question_topics, topics) that every
  -- user can read, so the isolation rests entirely on the exam_attempts join.
  select count(*) into v_n from public.v_topic_mastery;
  if v_n <> 0 then raise exception 'LEAK via view: intruder sees % rows in v_topic_mastery', v_n; end if;

  -- v_topic_practice is the finest-grained user-keyed view in the schema: one
  -- row per question answered. If security_invoker were ever dropped from it,
  -- this would hand over another student's entire answer history.
  select count(*) into v_n from public.v_topic_practice;
  if v_n <> 0 then raise exception 'LEAK via view: intruder sees % rows in v_topic_practice', v_n; end if;

  raise notice 'intruder sees 0 rows in every owned table and every view';

  -- Writing another user's row must fail the WITH CHECK, not silently succeed.
  v_failed := false;
  begin
    insert into public.exam_attempts (user_id, paper_id, local_date)
    values (v_owner, '0625_s24_11', current_date);
  exception when insufficient_privilege then
    v_failed := true;
  end;
  if not v_failed then raise exception 'LEAK: intruder inserted a row owned by someone else'; end if;
  raise notice 'intruder cannot insert rows owned by another user';

  -- Nor attach a child row to someone else's attempt.
  v_failed := false;
  begin
    insert into public.attempt_events
      (exam_attempt_id, seq, question_number, element_type, action_type, elapsed_ms)
    values (v_attempt, 999999, 1, 'highlight', 'setCorrect', 0);
  exception when insufficient_privilege then
    v_failed := true;
  end;
  if not v_failed then raise exception 'LEAK: intruder attached an event to another user''s attempt'; end if;
  raise notice 'intruder cannot attach child rows to another user''s attempt';

  -- Reference data stays readable - the app is unusable otherwise.
  select count(*) into v_n from public.subjects;
  if v_n = 0 then raise exception 'reference data unreadable: subjects returned 0 rows'; end if;
  raise notice 'reference data readable: % subjects', v_n;

  -- Topic tagging is reference data too: readable, and read-only. A client
  -- that could retag questions could move its own weak topics onto strong
  -- ones, which is the whole point of the mastery view.
  select count(*) into v_n from public.question_topics;
  if v_n = 0 then raise exception 'reference data unreadable: question_topics returned 0 rows'; end if;
  raise notice 'reference data readable: % question topic tags', v_n;

  v_failed := false;
  begin
    insert into public.question_topics (paper_id, question_number, topic_id)
    select '0625_s24_11', 1, id from public.topics limit 1;
  exception when insufficient_privilege then
    v_failed := true;
  end;
  if not v_failed then raise exception 'LEAK: a client tagged a question'; end if;

  v_failed := false;
  begin
    delete from public.question_topics where true;
  exception when insufficient_privilege then
    v_failed := true;
  end;
  if not v_failed then raise exception 'LEAK: a client deleted topic tags'; end if;
  raise notice 'question topic tags are not client-writable';

  -- ...but not writable. The answer key must not be rewritable by a client,
  -- or one user could change everybody's marks.
  v_failed := false;
  begin
    update public.paper_answers set correct_option = 0 where true;
  exception when insufficient_privilege then
    v_failed := true;
  end;
  if not v_failed then raise exception 'LEAK: a client rewrote the answer key'; end if;
  raise notice 'answer key is not client-rewritable';

  -- fetch-pdf now owns key installation. Even a brand-new paper is not a
  -- browser write: first-writer control was enough to poison persisted stats.
  v_failed := false;
  begin
    insert into public.paper_answer_keys (paper_id, question_count)
    values ('9999_s25_11', 40);
  exception when insufficient_privilege then
    v_failed := true;
  end;
  if not v_failed then raise exception 'LEAK: client installed a new answer key'; end if;
  raise notice 'client cannot install a new answer key';

  v_failed := false;
  begin
    insert into public.paper_answer_keys (paper_id, question_count)
    values ('9999_s25_11', 999)
    on conflict (paper_id) do update set question_count = excluded.question_count;
  exception when insufficient_privilege then
    v_failed := true;
  end;
  if not v_failed then raise exception 'LEAK: client overwrote an existing answer key'; end if;
  raise notice 'client cannot overwrite an existing answer key';

  reset role;
  raise notice 'test_solver_rls: all assertions passed';
end $$;

rollback;
