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

  reset role;
  raise notice 'test_solver_rls: all assertions passed';
end $$;

rollback;
