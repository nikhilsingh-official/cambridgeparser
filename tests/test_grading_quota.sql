-- ==========================================================================
--
-- Coverage for the quota logic that moved out of api/_quota.py and into
-- consume_grading_quota(). The Python side keeps tests for how it reads the
-- verdict (tests/test_rate_limit.py); this covers the arithmetic itself, which
-- needs a real transaction and a real row lock to mean anything.
--
-- Run against a local stack:
--     supabase db reset
--     psql "$SUPABASE_DB_URL" -f tests/test_grading_quota.sql
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

-- Ageing a window is test scaffolding, not something a caller can do:
-- `authenticated` has no UPDATE on grading_quotas, which is the point. Drop
-- back to the owning role for those writes.
create or replace function pg_temp.as_admin() returns void
language plpgsql as $$
begin
  perform set_config('role', 'postgres', true);
end;
$$;

do $$
declare
  alice uuid := '11111111-1111-1111-1111-111111111111';
  bob   uuid := '22222222-2222-2222-2222-222222222222';
  v     jsonb;
  i     integer;
begin
  -- auth.users has FK dependants, so seed the two identities directly.
  insert into auth.users (id, email) values (alice, 'alice@example.test')
    on conflict (id) do nothing;
  insert into auth.users (id, email) values (bob, 'bob@example.test')
    on conflict (id) do nothing;

  ------------------------------------------------------------------ burst
  perform pg_temp.act_as(alice);

  -- The first 8 calls in the window are allowed, and `remaining` counts down.
  for i in 1..8 loop
    v := public.consume_grading_quota();
    if (v->>'allowed')::boolean is not true then
      raise exception 'call % should have been allowed, got %', i, v;
    end if;
    if (v->>'remaining')::integer <> 8 - i then
      raise exception 'call % expected remaining %, got %', i, 8 - i, v->>'remaining';
    end if;
  end loop;

  -- The 9th is refused, names the burst limit, and asks for a real wait.
  v := public.consume_grading_quota();
  if (v->>'allowed')::boolean is not false then
    raise exception 'the 9th call in 10 minutes must be refused, got %', v;
  end if;
  if (v->>'limit')::integer <> 8 then
    raise exception 'expected limit 8, got %', v->>'limit';
  end if;
  if (v->>'window') <> 'burst' then
    raise exception 'expected the burst window to be the one that tripped, got %', v->>'window';
  end if;
  if (v->>'retry_after_seconds')::integer <= 0 then
    raise exception 'retry_after_seconds must be positive, got %', v->>'retry_after_seconds';
  end if;

  ------------------------------------------------- windows are independent
  -- Age the burst window past its 10 minutes; the daily count must survive it.
  perform pg_temp.as_admin();
  update public.grading_quotas
     set burst_started_at = now() - interval '11 minutes'
   where user_id = alice;
  perform pg_temp.act_as(alice);

  v := public.consume_grading_quota();
  if (v->>'allowed')::boolean is not true then
    raise exception 'an expired burst window must reset, got %', v;
  end if;
  -- 9 of the 50 daily are now spent, so daily is the smaller remainder only
  -- once burst has been refilled: burst has 7 left, daily has 41.
  if (v->>'remaining')::integer <> 7 then
    raise exception 'expected 7 burst remaining after reset, got %', v->>'remaining';
  end if;
  if (select daily_count from public.grading_quotas where user_id = alice) <> 9 then
    raise exception 'resetting the burst window must not reset the daily count';
  end if;

  ------------------------------------------------------------------ daily
  perform pg_temp.as_admin();
  update public.grading_quotas
     set daily_count = 50, burst_count = 0, burst_started_at = now()
   where user_id = alice;
  perform pg_temp.act_as(alice);

  v := public.consume_grading_quota();
  if (v->>'allowed')::boolean is not false then
    raise exception 'an exhausted daily window must refuse, got %', v;
  end if;
  if (v->>'window') <> 'daily' then
    raise exception 'expected the daily window to trip, got %', v->>'window';
  end if;

  ------------------------------------------------------------- isolation
  -- Bob is unaffected by anything Alice spent.
  perform pg_temp.act_as(bob);
  v := public.consume_grading_quota();
  if (v->>'allowed')::boolean is not true then
    raise exception 'one user exhausting quota must not block another, got %', v;
  end if;
  if (v->>'remaining')::integer <> 7 then
    raise exception 'bob should start fresh, got remaining %', v->>'remaining';
  end if;

  -- And cannot see Alice's counter through the API's policies.
  if exists (select 1 from public.grading_quotas where user_id = alice) then
    raise exception 'RLS must hide another user''s quota row';
  end if;

  ------------------------------------------------------- anonymous callers
  perform set_config('request.jwt.claim.sub', '', true);
  begin
    v := public.consume_grading_quota();
    raise exception 'an anonymous caller must be rejected, got %', v;
  exception
    when sqlstate '28000' then null;   -- expected
    when invalid_text_representation then null;  -- empty sub never parses to uuid
  end;

  raise notice 'consume_grading_quota: all assertions passed';
end;
$$;

rollback;
