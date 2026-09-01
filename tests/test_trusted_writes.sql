-- ==========================================================================
--
-- Security contract for server-owned grading inputs and append-only history.
-- Run after `supabase db reset`; the transaction is always rolled back.
-- ==========================================================================

\set ON_ERROR_STOP on

begin;

create or replace function pg_temp.act_as(p_role text, p_user uuid default null)
returns void language plpgsql as $$
begin
  perform set_config('role', p_role, true);
  perform set_config('request.jwt.claim.sub', coalesce(p_user::text, ''), true);
  perform set_config(
    'request.jwt.claims',
    json_build_object('sub', p_user, 'role', p_role)::text,
    true
  );
end;
$$;

do $$
declare
  alice uuid := 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  attempt_id uuid;
  invalid_attempt_id uuid;
  completion_id uuid := 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
  result jsonb;
  failed boolean;
  protected_table text;
  privilege text;
begin
  insert into auth.users (id, email) values (alice, 'trusted-writes@example.test')
    on conflict (id) do nothing;

  -- policy tests prove row predicates; this ACL matrix proves there is no
  -- direct write verb capable of reaching those policies in the first place.
  foreach protected_table in array array[
    'paper_answer_keys', 'paper_answers', 'exam_attempts', 'question_attempts',
    'question_metrics', 'attempt_events', 'ide_progress', 'ide_attempts'
  ] loop
    foreach privilege in array array['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'] loop
      if has_table_privilege('authenticated', 'public.' || protected_table, privilege) then
        raise exception 'authenticated retains % on %', privilege, protected_table;
      end if;
    end loop;
  end loop;
  if has_function_privilege(
    'authenticated',
    'public.install_verified_answer_key(text,text,text,integer,jsonb)',
    'EXECUTE'
  ) or has_function_privilege(
    'authenticated',
    'public.record_ide_attempt_trusted(uuid,text,integer,integer,text,text,jsonb,text)',
    'EXECUTE'
  ) then
    raise exception 'authenticated can execute a service-only RPC';
  end if;

  perform pg_temp.act_as('authenticated', alice);

  failed := false;
  begin
    insert into public.paper_answer_keys (paper_id, question_count)
    values ('9999_s25_11', 2);
  exception when insufficient_privilege then failed := true;
  end;
  if not failed then raise exception 'authenticated user installed an answer key'; end if;

  failed := false;
  begin
    perform public.install_verified_answer_key(
      '9999_s25_11', 'https://example.test/ms.pdf', repeat('a', 64), 1,
      '[{"question_number":1,"correct_option":0,"option_count":4,"marks":1}]'::jsonb
    );
  exception when insufficient_privilege then failed := true;
  end;
  if not failed then raise exception 'authenticated user called trusted key RPC'; end if;

  perform pg_temp.act_as('service_role');
  perform public.install_verified_answer_key(
    '9999_s25_11', 'https://example.test/ms.pdf', repeat('a', 64), 1,
    '[{"question_number":1,"correct_option":0,"option_count":4,"marks":1},'
    '{"question_number":2,"correct_option":1,"option_count":4,"marks":1}]'::jsonb
  );

  -- provenance is mandatory, not merely well-formed when present.
  failed := false;
  begin
    perform public.install_verified_answer_key(
      '9999_s25_12', 'https://example.test/ms.pdf', null, 1,
      '[{"question_number":1,"correct_option":0,"option_count":4,"marks":1}]'::jsonb
    );
  exception when invalid_parameter_value then failed := true;
  end;
  if not failed then raise exception 'trusted key accepted a null source hash'; end if;

  perform pg_temp.act_as('authenticated', alice);
  -- every accepted telemetry row must have a known event vocabulary.
  invalid_attempt_id := public.start_exam_attempt('9999_s25_11', 'UTC');
  failed := false;
  begin
    perform public.finalize_exam_attempt(
      invalid_attempt_id,
      gen_random_uuid(),
      1000,
      '[{"question_number":1,"selected_option":0},{"question_number":2,"selected_option":0}]'::jsonb,
      '[{"seq":0,"question_number":1,"elapsed_ms":1}]'::jsonb
    );
  exception when invalid_parameter_value then failed := true;
  end;
  if not failed then raise exception 'completion accepted an event with no type or action'; end if;
  perform public.abandon_exam_attempt(invalid_attempt_id, 1000);

  attempt_id := public.start_exam_attempt('9999_s25_11', 'Europe/London');
  result := public.finalize_exam_attempt(
    attempt_id,
    completion_id,
    120000,
    '[{"question_number":1,"selected_option":0,"eliminated_mask":0,"time_spent_ms":5000,
       "hesitation_ms":null,"option_switch_count":0,"elimination_reversal_count":0,
       "revisit_count":0,"marked_for_review_count":0,"marked_as_difficult_count":0,
       "marked_for_save_count":0,"stable_elimination_ratio":0,"exploration_depth":0,
       "exploration_breadth":0,"confidence":0.8,"difficulty":0.2,"interest":0.4},
      {"question_number":2,"selected_option":0,"eliminated_mask":0,"time_spent_ms":6000,
       "hesitation_ms":null,"option_switch_count":0,"elimination_reversal_count":0,
       "revisit_count":0,"marked_for_review_count":0,"marked_as_difficult_count":0,
       "marked_for_save_count":0,"stable_elimination_ratio":0,"exploration_depth":0,
       "exploration_breadth":0,"confidence":0.5,"difficulty":0.5,"interest":0.5}]'::jsonb,
    '[]'::jsonb
  );
  if result->>'status' <> 'completed' or (result->>'questions_correct')::int <> 1 then
    raise exception 'unexpected finalization result: %', result;
  end if;

  -- A response lost in transit can be retried with the same idempotency key.
  if public.finalize_exam_attempt(
       attempt_id, completion_id, 120000,
       '[{"question_number":1,"selected_option":0},{"question_number":2,"selected_option":0}]'::jsonb,
       '[]'::jsonb
     )->>'status' <> 'completed' then
    raise exception 'idempotent retry did not return the completed attempt';
  end if;

  failed := false;
  begin
    update public.exam_attempts set status = 'in_progress' where id = attempt_id;
  exception when insufficient_privilege then failed := true;
  end;
  if not failed then raise exception 'authenticated user mutated completed attempt'; end if;

  failed := false;
  begin
    delete from public.question_attempts where exam_attempt_id = attempt_id;
  exception when insufficient_privilege then failed := true;
  end;
  if not failed then raise exception 'authenticated user erased attempt answers'; end if;

  failed := false;
  begin
    perform public.record_ide_attempt_trusted(alice, 'forged', 6, 6);
  exception when insufficient_privilege then failed := true;
  end;
  if not failed then raise exception 'authenticated user forged an IDE score'; end if;

  perform pg_temp.act_as('service_role');
  perform public.record_ide_attempt_trusted(alice, 'trusted', 4, 6);
  perform pg_temp.act_as('postgres');
  if not exists (
    select 1 from public.ide_attempts
    where user_id = alice and record_id = 'trusted' and score = 4
  ) then
    raise exception 'trusted IDE recorder did not persist the result';
  end if;

  raise notice 'trusted write boundary: all assertions passed';
end;
$$;

rollback;
