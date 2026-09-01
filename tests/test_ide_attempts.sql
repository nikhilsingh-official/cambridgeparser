-- ==========================================================================
--
-- Coverage for the IDE attempt log added in
-- supabase/migrations/00000000000006_ide_attempts.sql.
--
-- Three things here are claims about a student's record rather than about
-- code, and all three are checked below because none of them is recoverable if
-- it turns out to be wrong later:
--   1. every submission is logged, including the ones that scored worse;
--   2. a logged submission cannot afterwards be edited or erased;
--   3. the log and the progress row can never disagree about how many
--      submissions there were.
--
-- Run against a local stack:
--     supabase db reset
--     psql "$SUPABASE_DB_URL" -f tests/test_ide_attempts.sql
--
-- Exits non-zero on the first failed assertion.
-- ==========================================================================

\set ON_ERROR_STOP on

begin;

-- A signed-in caller is simulated by setting the JWT claims PostgREST would
-- set. auth.uid() reads request.jwt.claim.sub.
create or replace function pg_temp.act_as(p_user uuid) returns void
language plpgsql as $$
begin
  perform set_config('request.jwt.claim.sub', p_user::text, true);
  perform set_config('role', 'authenticated', true);
end;
$$;

create or replace function pg_temp.as_admin() returns void
language plpgsql as $$
begin
  perform set_config('role', 'postgres', true);
end;
$$;

-- simulate the trusted Edge Function without granting its RPC to the
-- authenticated browser role. The wrapper is test-only and owned by postgres.
create or replace function pg_temp.record_trusted(
  p_user_id uuid,
  p_record_id text,
  p_score integer,
  p_max_marks integer,
  p_source text default null,
  p_answer_kind text default null,
  p_points jsonb default null,
  p_client_timezone text default null
) returns public.ide_progress
language sql
security definer
set search_path = public
as $$
  select public.record_ide_attempt_trusted(
    p_user_id, p_record_id, p_score, p_max_marks, p_source,
    p_answer_kind, p_points, p_client_timezone
  );
$$;

do $$
declare
  alice uuid := '11111111-1111-1111-1111-111111111111';
  bob   uuid := '22222222-2222-2222-2222-222222222222';
  q     text := 'record-4210';
  v_row public.ide_progress;
  n     integer;
  d1    date;
  d2    date;
begin
  insert into auth.users (id, email) values (alice, 'alice@example.test')
    on conflict (id) do nothing;
  insert into auth.users (id, email) values (bob, 'bob@example.test')
    on conflict (id) do nothing;

  ------------------------------------------------------- a first submission
  perform pg_temp.act_as(alice);

  v_row := pg_temp.record_trusted(
    alice, q, 3, 6, 'OUTPUT "hi"', 'pseudocode',
    '[{"awarded": true, "marks_awarded": 3}]'::jsonb, 'Europe/London');

  if v_row.status <> 'attempted' then
    raise exception '3/6 is not solved, got status %', v_row.status;
  end if;
  if v_row.best_score <> 3 or v_row.attempts <> 1 then
    raise exception 'expected best 3 / 1 attempt, got % / %',
      v_row.best_score, v_row.attempts;
  end if;

  select count(*) into n from public.ide_attempts
   where user_id = alice and record_id = q;
  if n <> 1 then
    raise exception 'the submission must be logged, found % rows', n;
  end if;

  -- The submitted answer and the marking points survive, not just the score.
  if not exists (
    select 1 from public.ide_attempts
     where user_id = alice and record_id = q
       and source = 'OUTPUT "hi"'
       and answer_kind = 'pseudocode'
       and points->0->>'marks_awarded' = '3')
  then
    raise exception 'the log must keep the answer and the marking points';
  end if;

  --------------------------------------------- a WORSE second submission
  -- This is the case the upsert alone destroys: ide_progress keeps the 3 and
  -- forgets that a 1/6 ever happened. The log must not.
  v_row := pg_temp.record_trusted(alice, q, 1, 6, 'OUTPUT', 'pseudocode', null, 'Europe/London');

  if v_row.best_score <> 3 then
    raise exception 'a worse attempt must not lower the best score, got %',
      v_row.best_score;
  end if;
  if v_row.attempts <> 2 then
    raise exception 'expected 2 attempts, got %', v_row.attempts;
  end if;

  select count(*) into n from public.ide_attempts
   where user_id = alice and record_id = q;
  if n <> 2 then
    raise exception 'the worse submission must still be logged, found % rows', n;
  end if;
  if not exists (select 1 from public.ide_attempts
                  where user_id = alice and record_id = q and score = 1) then
    raise exception 'the 1/6 is missing from the log';
  end if;

  ------------------------------------------------ 'solved' is still absorbing
  v_row := pg_temp.record_trusted(alice, q, 6, 6, 'OUTPUT "hi"', 'pseudocode', null, 'Europe/London');
  if v_row.status <> 'solved' then
    raise exception '6/6 must solve, got %', v_row.status;
  end if;
  v_row := pg_temp.record_trusted(alice, q, 0, 6, '', 'pseudocode', null, 'Europe/London');
  if v_row.status <> 'solved' then
    raise exception 'a later 0/6 must not un-solve, got %', v_row.status;
  end if;
  -- ...and the 0/6 is on the record anyway, which is the whole point of a log.
  if not exists (select 1 from public.ide_attempts
                  where user_id = alice and record_id = q and score = 0) then
    raise exception 'the 0/6 after solving is missing from the log';
  end if;

  ----------------------------------------- the log and the counter agree
  select submissions into n from public.v_ide_stats where user_id = alice;
  if n <> (select count(*) from public.ide_attempts where user_id = alice) then
    raise exception 'v_ide_stats.submissions (%) disagrees with the log (%)',
      n, (select count(*) from public.ide_attempts where user_id = alice);
  end if;
  if (select solved from public.v_ide_stats where user_id = alice) <> 1 then
    raise exception 'one question was solved';
  end if;

  ------------------------------------------------------------ append-only
  -- Both gates: `authenticated` holds no UPDATE/DELETE grant, and there is no
  -- policy that would admit one either.
  begin
    update public.ide_attempts set score = 6 where user_id = alice;
    raise exception 'a student must not be able to revise a past submission';
  exception when insufficient_privilege then null;   -- expected
  end;
  begin
    delete from public.ide_attempts where user_id = alice;
    raise exception 'a student must not be able to erase a past submission';
  exception when insufficient_privilege then null;   -- expected
  end;

  ------------------------------------------------------ the timezone argument
  -- Two zones 25 hours apart can never share a calendar date, so if the
  -- argument were ignored these would be equal.
  perform pg_temp.record_trusted(alice, 'tz-a', 1, 1, null, null, null, 'Pacific/Kiritimati');
  perform pg_temp.record_trusted(alice, 'tz-b', 1, 1, null, null, null, 'Pacific/Niue');
  select local_date into d1 from public.ide_attempts where record_id = 'tz-a';
  select local_date into d2 from public.ide_attempts where record_id = 'tz-b';
  if d1 = d2 then
    raise exception 'client_timezone was ignored: both filed on %', d1;
  end if;

  -- A nonsense zone must not cost the student their submission.
  perform pg_temp.record_trusted(alice, 'tz-bad', 1, 1, null, null, null, 'Not/AZone');
  if (select local_date from public.ide_attempts where record_id = 'tz-bad')
     <> (now() at time zone 'UTC')::date then
    raise exception 'an unknown timezone must fall back to UTC';
  end if;

  ---------------------------------------------------------------- v_ide_daily
  if (select submissions from public.v_ide_daily
       where user_id = alice and local_date = d1) is null then
    raise exception 'v_ide_daily must have a row for the day work happened';
  end if;

  ------------------------------------------------------------- other users
  perform pg_temp.act_as(bob);
  if exists (select 1 from public.ide_attempts where user_id = alice) then
    raise exception 'RLS must hide another user''s submissions';
  end if;
  if exists (select 1 from public.v_ide_daily where user_id = alice) then
    raise exception 'v_ide_daily must not leak another user''s days';
  end if;
  -- And cannot file a submission in Alice's name.
  begin
    insert into public.ide_attempts
      (user_id, record_id, score, max_marks, local_date)
    values (alice, 'forged', 6, 6, current_date);
    raise exception 'one user must not be able to write another user''s log';
  exception when insufficient_privilege then null;   -- expected
  end;

  ------------------------------------------------------- anonymous callers
  perform set_config('request.jwt.claim.sub', '', true);
  begin
    v_row := public.record_ide_attempt_trusted(alice, 'anon', 1, 1);
    raise exception 'a browser caller must be rejected, got %', v_row;
  exception
    when insufficient_privilege then null;        -- expected
  end;

  raise notice 'record_ide_attempt / ide_attempts: all assertions passed';
end;
$$;

rollback;
