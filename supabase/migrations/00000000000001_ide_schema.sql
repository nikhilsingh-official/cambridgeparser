-- ==========================================================================
--
-- The pseudocode IDE's own tables, replacing the Firebase Realtime Database
-- subtree that used to live at users/$uid/ and gradingQuotas/$uid/.
--
-- Shares auth.users with the Soluer solver: one account, both apps. That is
-- the whole reason this migration exists (see docs/roadmap.md A1), so nothing
-- here defines its own notion of a user.
--
-- RLS is ON for every table below, unlike the solver's tables. The IDE's
-- grading endpoint runs on Vercel with only the anon key, so the database -
-- not the caller - has to be what stops one user reading another's rows.
-- ==========================================================================

-- --------------------------------------------------------------------------
-- Profiles. The RTDB shape was users/$uid/profile/{email, displayName,
-- createdAt, lastLoginAt, schemaVersion}. `schemaVersion` is dropped: it
-- existed because RTDB is schemaless and had no other way to version a shape.
-- Postgres has migrations.
-- --------------------------------------------------------------------------
create table if not exists public.ide_profiles (
  user_id       uuid primary key references auth.users (id) on delete cascade,
  email         text,
  display_name  text,
  created_at    timestamptz not null default now(),
  last_login_at timestamptz not null default now()
);

alter table public.ide_profiles enable row level security;

create policy ide_profiles_select_own on public.ide_profiles
  for select using (auth.uid() = user_id);
create policy ide_profiles_insert_own on public.ide_profiles
  for insert with check (auth.uid() = user_id);
create policy ide_profiles_update_own on public.ide_profiles
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- --------------------------------------------------------------------------
-- Progress, one row per (user, question record).
--
-- record_id is text because the IDE keys questions by the record id from
-- pseudocode_question_records.json, which is pipeline-owned and renumbers
-- between corpus builds. Storing it as text keeps this table from pretending
-- to a foreign key it cannot honour.
--
-- The RTDB version enforced status via security rules; here it is an enum-ish
-- check, and the "never go backwards" rule that used to live in a client-side
-- runTransaction is now in record_ide_attempt() below - it was never safe in
-- the client.
-- --------------------------------------------------------------------------
create table if not exists public.ide_progress (
  user_id     uuid not null references auth.users (id) on delete cascade,
  record_id   text not null,
  status      text not null default 'not_started'
              check (status in ('not_started', 'attempted', 'solved')),
  best_score  integer not null default 0 check (best_score >= 0),
  max_marks   integer not null default 0 check (max_marks >= 0),
  attempts    integer not null default 0 check (attempts >= 0),
  last_source text,
  updated_at  timestamptz not null default now(),
  primary key (user_id, record_id)
);

alter table public.ide_progress enable row level security;

create policy ide_progress_select_own on public.ide_progress
  for select using (auth.uid() = user_id);
create policy ide_progress_insert_own on public.ide_progress
  for insert with check (auth.uid() = user_id);
create policy ide_progress_update_own on public.ide_progress
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- The RTDB `stats/` subtree held denormalised {attempted, solved} counters
-- because RTDB cannot aggregate. Postgres can, so it is a view: one fewer
-- thing that can disagree with the rows it summarises.
--
-- security_invoker is ESSENTIAL and not the default. Without it a view runs
-- with its owner's privileges, which means it reads ide_progress as postgres
-- and RLS never applies - every user would see every user's counters through
-- it. Verified: the view returns only the caller's row with this set, and all
-- rows without it.
create or replace view public.v_ide_stats
  with (security_invoker = true) as
select
  user_id,
  count(*) filter (where status in ('attempted', 'solved')) as attempted,
  count(*) filter (where status = 'solved')                 as solved
from public.ide_progress
group by user_id;

-- --------------------------------------------------------------------------
-- record_ide_attempt: one graded submission.
--
-- Replaces the client-side runTransaction. Keeping the best score and never
-- un-solving a solved question are integrity rules, and integrity rules that
-- live in the client are advisory. `security invoker` so RLS still applies -
-- this function needs no elevation, it only ever touches the caller's row.
-- --------------------------------------------------------------------------
create or replace function public.record_ide_attempt(
  p_record_id text,
  p_score     integer,
  p_max_marks integer,
  p_source    text default null
) returns public.ide_progress
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_user_id uuid := auth.uid();
  v_solved  boolean := p_max_marks > 0 and p_score >= p_max_marks;
  v_row     public.ide_progress;
begin
  if v_user_id is null then
    raise exception 'record_ide_attempt requires an authenticated caller'
      using errcode = '28000';
  end if;

  insert into public.ide_progress as p
    (user_id, record_id, status, best_score, max_marks, attempts, last_source, updated_at)
  values
    (v_user_id, p_record_id,
     case when v_solved then 'solved' else 'attempted' end,
     greatest(p_score, 0), p_max_marks, 1, p_source, now())
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
-- Grading quotas.
--
-- Two fixed windows, matching the limits the Firebase rules enforced:
-- 8 requests per 10 minutes and 50 per day. The old design pushed this into
-- RTDB security-rule expressions plus an ETag compare-and-set loop in the
-- Vercel function, because Vercel deliberately held no admin credential.
--
-- Same constraint here, better mechanism: the counter table is readable by its
-- owner but writable by NOBODY through the API. Only consume_grading_quota()
-- writes it, and that function is `security definer`, so the increment is
-- atomic inside one statement and a caller cannot forge or reset their own
-- counter. Vercel still needs nothing but the anon key and the user's token.
-- --------------------------------------------------------------------------
create table if not exists public.grading_quotas (
  user_id            uuid primary key references auth.users (id) on delete cascade,
  burst_started_at   timestamptz not null default now(),
  burst_count        integer     not null default 0,
  daily_started_at   timestamptz not null default now(),
  daily_count        integer     not null default 0
);

alter table public.grading_quotas enable row level security;

-- Read-only, and only your own. No insert/update/delete policy exists, so the
-- table is unwritable through PostgREST by design.
create policy grading_quotas_select_own on public.grading_quotas
  for select using (auth.uid() = user_id);

create or replace function public.consume_grading_quota()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  burst_limit  constant integer  := 8;
  burst_window constant interval := interval '10 minutes';
  daily_limit  constant integer  := 50;
  daily_window constant interval := interval '24 hours';

  v_user_id uuid := auth.uid();
  v_now     timestamptz := now();
  v_row     public.grading_quotas;
  v_retry   integer;
begin
  if v_user_id is null then
    raise exception 'consume_grading_quota requires an authenticated caller'
      using errcode = '28000';
  end if;

  -- Materialise the row and hold it for the rest of the transaction. Two
  -- concurrent submissions therefore serialise here rather than both reading
  -- the same count and both incrementing it to the same value.
  insert into public.grading_quotas (user_id, burst_started_at, daily_started_at)
  values (v_user_id, v_now, v_now)
  on conflict (user_id) do nothing;

  select * into v_row from public.grading_quotas
   where user_id = v_user_id
     for update;

  -- Roll expired windows before testing them.
  if v_now >= v_row.burst_started_at + burst_window then
    v_row.burst_started_at := v_now;
    v_row.burst_count := 0;
  end if;
  if v_now >= v_row.daily_started_at + daily_window then
    v_row.daily_started_at := v_now;
    v_row.daily_count := 0;
  end if;

  if v_row.burst_count >= burst_limit then
    v_retry := greatest(1, ceil(extract(epoch from
                 (v_row.burst_started_at + burst_window) - v_now))::integer);
    return jsonb_build_object('allowed', false, 'limit', burst_limit,
                              'window', 'burst', 'retry_after_seconds', v_retry);
  end if;
  if v_row.daily_count >= daily_limit then
    v_retry := greatest(1, ceil(extract(epoch from
                 (v_row.daily_started_at + daily_window) - v_now))::integer);
    return jsonb_build_object('allowed', false, 'limit', daily_limit,
                              'window', 'daily', 'retry_after_seconds', v_retry);
  end if;

  update public.grading_quotas set
    burst_started_at = v_row.burst_started_at,
    burst_count      = v_row.burst_count + 1,
    daily_started_at = v_row.daily_started_at,
    daily_count      = v_row.daily_count + 1
  where user_id = v_user_id
  returning * into v_row;

  return jsonb_build_object(
    'allowed', true,
    'remaining', least(burst_limit - v_row.burst_count,
                       daily_limit - v_row.daily_count)
  );
end;
$$;

-- security definer functions are executable by PUBLIC unless revoked. Only a
-- signed-in caller should be able to spend quota, and the function itself
-- rejects a null auth.uid(), but be explicit about who may call it.
revoke all on function public.consume_grading_quota() from public;
grant execute on function public.consume_grading_quota() to authenticated;
revoke all on function public.record_ide_attempt(text, integer, integer, text) from public;
grant execute on function public.record_ide_attempt(text, integer, integer, text) to authenticated;

-- --------------------------------------------------------------------------
-- Table privileges.
--
-- RLS decides WHICH ROWS a caller may touch; it does not grant the right to
-- touch the table at all. Both are required, and this project's default
-- privileges grant `authenticated` only REFERENCES/TRIGGER/TRUNCATE - so
-- without the grants below, every statement fails with "permission denied for
-- table" before a policy is ever consulted. Verified by running it.
--
-- No grants to `anon`: nothing here is readable signed out.
-- --------------------------------------------------------------------------
grant select, insert, update on public.ide_profiles to authenticated;
grant select, insert, update on public.ide_progress to authenticated;
grant select on public.v_ide_stats to authenticated;

-- Deliberately SELECT only. record_ide_attempt() is `security invoker` and so
-- needs the caller's own insert/update above, but consume_grading_quota() is
-- `security definer` and runs as the owner - so the client needs no write
-- privilege on the counter, and must not have one.
grant select on public.grading_quotas to authenticated;
