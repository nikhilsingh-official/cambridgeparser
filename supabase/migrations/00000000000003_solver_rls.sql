-- ==========================================================================
--
-- Row Level Security for the solver's tables.
--
-- WHY THIS IS A SEPARATE MIGRATION
-- The IDE's tables shipped with RLS on from the start (00000000000001). The
-- solver's did not, deliberately: development ran on emulators and the client
-- queries all filter on an explicit user_id. That left the database in a worse
-- state than having no RLS anywhere - the three tables storing nothing were
-- locked down, and the eleven holding every student's attempt history were
-- open to any authenticated caller. Supabase's anon key is public by design,
-- so "authenticated" is "anyone who signed up".
--
-- THREE CLASSES OF TABLE
--   owned      - rows belong to one user. Full CRUD on your own, nothing on
--                anyone else's.
--   derived    - rows belong to a user only through their parent attempt.
--                Reached by subquery; there is no user_id column to filter on,
--                and adding one would be denormalisation that can drift.
--   reference  - syllabus and answer-key data, the same for everybody.
--                Readable by any signed-in user, never writable by them.
--
-- `(select auth.uid())` rather than a bare `auth.uid()` is deliberate. The
-- bare call is volatile-ish to the planner and gets re-evaluated PER ROW; as a
-- scalar subquery it becomes an InitPlan evaluated once for the statement.
-- On attempt_events - the largest table here - that is the difference between
-- one call and one per event.
--
-- NOT ADDRESSED HERE: paper_answers stays readable by any signed-in user,
-- because the client still marks the paper and needs the key. That is roadmap
-- B4 (move the write into fetch-pdf and stop shipping the key), and it is a
-- correctness problem about forgeable scores, not an isolation problem - the
-- key is the same for everyone, so no policy can help.
-- ==========================================================================

-- --------------------------------------------------------------------------
-- Owned: a user_id column to compare against directly.
-- --------------------------------------------------------------------------

alter table public.exam_attempts enable row level security;

create policy exam_attempts_select_own on public.exam_attempts
  for select using ((select auth.uid()) = user_id);
create policy exam_attempts_insert_own on public.exam_attempts
  for insert with check ((select auth.uid()) = user_id);
create policy exam_attempts_update_own on public.exam_attempts
  for update using ((select auth.uid()) = user_id)
          with check ((select auth.uid()) = user_id);
create policy exam_attempts_delete_own on public.exam_attempts
  for delete using ((select auth.uid()) = user_id);

alter table public.goals enable row level security;

create policy goals_select_own on public.goals
  for select using ((select auth.uid()) = user_id);
create policy goals_insert_own on public.goals
  for insert with check ((select auth.uid()) = user_id);
create policy goals_update_own on public.goals
  for update using ((select auth.uid()) = user_id)
          with check ((select auth.uid()) = user_id);
create policy goals_delete_own on public.goals
  for delete using ((select auth.uid()) = user_id);

-- profiles.id IS the user id - it references auth.users(id) directly.
alter table public.profiles enable row level security;

create policy profiles_select_own on public.profiles
  for select using ((select auth.uid()) = id);
create policy profiles_insert_own on public.profiles
  for insert with check ((select auth.uid()) = id);
create policy profiles_update_own on public.profiles
  for update using ((select auth.uid()) = id)
          with check ((select auth.uid()) = id);

-- The table was granted SELECT only, so even with a policy the client could
-- not create its own row. Nothing writes profiles yet (roadmap B5); this makes
-- the write possible when something does, rather than leaving a policy that
-- can never fire.
grant insert, update on public.profiles to authenticated;

-- --------------------------------------------------------------------------
-- Derived: ownership is a property of the parent attempt.
--
-- Written as EXISTS rather than `in (select ...)`: both plan the same way here,
-- but EXISTS short-circuits on the first match and reads as the question being
-- asked - "is there an attempt of mine that this row hangs off?".
-- --------------------------------------------------------------------------

alter table public.question_attempts enable row level security;

create policy question_attempts_own on public.question_attempts
  for all
  using (exists (
    select 1 from public.exam_attempts ea
    where ea.id = question_attempts.exam_attempt_id
      and ea.user_id = (select auth.uid())
  ))
  with check (exists (
    select 1 from public.exam_attempts ea
    where ea.id = question_attempts.exam_attempt_id
      and ea.user_id = (select auth.uid())
  ));

alter table public.attempt_events enable row level security;

create policy attempt_events_own on public.attempt_events
  for all
  using (exists (
    select 1 from public.exam_attempts ea
    where ea.id = attempt_events.exam_attempt_id
      and ea.user_id = (select auth.uid())
  ))
  with check (exists (
    select 1 from public.exam_attempts ea
    where ea.id = attempt_events.exam_attempt_id
      and ea.user_id = (select auth.uid())
  ));

-- Two hops: question_metrics -> question_attempts -> exam_attempts. Both are
-- primary-key lookups, so the cost is two index probes per row and the
-- InitPlan'd auth.uid() is shared across all of them.
alter table public.question_metrics enable row level security;

create policy question_metrics_own on public.question_metrics
  for all
  using (exists (
    select 1
    from public.question_attempts qa
    join public.exam_attempts ea on ea.id = qa.exam_attempt_id
    where qa.id = question_metrics.question_attempt_id
      and ea.user_id = (select auth.uid())
  ))
  with check (exists (
    select 1
    from public.question_attempts qa
    join public.exam_attempts ea on ea.id = qa.exam_attempt_id
    where qa.id = question_metrics.question_attempt_id
      and ea.user_id = (select auth.uid())
  ));

-- --------------------------------------------------------------------------
-- Reference: shared, read-only.
--
-- These carry no personal data, but RLS still goes ON. A table with RLS
-- disabled is invisible to the "is everything covered?" check; a table with
-- RLS on and a permissive read policy states the intent in the schema.
-- --------------------------------------------------------------------------

alter table public.subjects enable row level security;
create policy subjects_read on public.subjects
  for select to authenticated using (true);

alter table public.topics enable row level security;
create policy topics_read on public.topics
  for select to authenticated using (true);

alter table public.metrics_versions enable row level security;
create policy metrics_versions_read on public.metrics_versions
  for select to authenticated using (true);

-- The answer key. Readable by any signed-in user (the client marks the paper),
-- and insertable because cacheAnswerKey.ts populates it on first sit. NOT
-- updatable or deletable: once a paper's key is cached, a client must not be
-- able to rewrite it and change everyone's marks.
alter table public.paper_answer_keys enable row level security;
create policy paper_answer_keys_read on public.paper_answer_keys
  for select to authenticated using (true);
create policy paper_answer_keys_insert on public.paper_answer_keys
  for insert to authenticated with check (true);

alter table public.paper_answers enable row level security;
create policy paper_answers_read on public.paper_answers
  for select to authenticated using (true);
create policy paper_answers_insert on public.paper_answers
  for insert to authenticated with check (true);

-- The UPDATE grants handed out in the base migration are now wider than the
-- policies allow, which is confusing rather than dangerous. Revoke them so the
-- grant and the policy say the same thing.
revoke update, delete on public.paper_answer_keys from authenticated;
revoke update, delete on public.paper_answers   from authenticated;
revoke insert, update, delete on public.topics  from authenticated;
