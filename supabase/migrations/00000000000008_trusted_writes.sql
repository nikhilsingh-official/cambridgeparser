-- ==========================================================================
--
-- Move grading inputs and completed histories behind narrow RPC boundaries.
-- Existing answer keys are deliberately discarded: they were first-writer
-- controlled by authenticated clients and therefore have no trusted lineage.
-- Existing attempts survive with NULL correctness until fetch-pdf installs a
-- verified key and re-marks the paper.
-- ==========================================================================

alter table public.paper_answer_keys
  add column if not exists source_sha256 text,
  add column if not exists verified_at timestamptz,
  add column if not exists parser_version integer;

alter table public.paper_answer_keys
  drop constraint if exists paper_answer_keys_source_sha256_check;
alter table public.paper_answer_keys
  add constraint paper_answer_keys_source_sha256_check
  check (source_sha256 is null or source_sha256 ~ '^[0-9a-f]{64}$');

alter table public.exam_attempts
  add column if not exists completion_id uuid;
create unique index if not exists idx_exam_attempt_completion
  on public.exam_attempts (completion_id) where completion_id is not null;

-- The user explicitly chose to distrust every legacy key while retaining the
-- attempts. Do this before deleting the rows so no stale boolean survives.
update public.question_attempts set is_correct = null;
delete from public.paper_answer_keys;

create or replace function public.install_verified_answer_key(
  p_paper_id text,
  p_source_url text,
  p_source_sha256 text,
  p_parser_version integer,
  p_answers jsonb
) returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  v_count integer;
  v_distinct integer;
  v_min integer;
  v_max integer;
begin
  if p_paper_id !~ '^[0-9]{4}_[msw][0-9]{2}_[0-9]{1,2}$' then
    raise exception 'invalid paper id' using errcode = '22023';
  end if;
  if p_source_url is null or p_source_url !~ '^https://' then
    raise exception 'invalid source URL' using errcode = '22023';
  end if;
  if p_source_sha256 is null or p_source_sha256 !~ '^[0-9a-f]{64}$' then
    raise exception 'invalid source hash' using errcode = '22023';
  end if;
  if p_parser_version is null or p_parser_version < 1 then
    raise exception 'invalid parser version' using errcode = '22023';
  end if;
  if jsonb_typeof(p_answers) <> 'array' or jsonb_array_length(p_answers) = 0 then
    raise exception 'answers must be a non-empty array' using errcode = '22023';
  end if;

  select count(*), count(distinct question_number), min(question_number), max(question_number)
    into v_count, v_distinct, v_min, v_max
  from (
    select (item->>'question_number')::integer as question_number
    from jsonb_array_elements(p_answers) item
  ) parsed;

  if v_count <> v_distinct or v_min <> 1 or v_max <> v_count then
    raise exception 'question numbers must be unique and contiguous from 1'
      using errcode = '22023';
  end if;
  if exists (
    select 1 from jsonb_array_elements(p_answers) item
    where (item->>'option_count')::integer not between 2 and 8
       or (item->>'correct_option')::integer < 0
       or (item->>'correct_option')::integer >= (item->>'option_count')::integer
       or (item->>'marks')::integer < 1
  ) then
    raise exception 'answer row is outside supported bounds' using errcode = '22023';
  end if;

  -- One transaction and one paper-scoped lock make replacement atomic even
  -- when several students open the same uncached paper together.
  perform pg_advisory_xact_lock(hashtextextended(p_paper_id, 0));

  if exists (
    select 1 from public.paper_answer_keys key
    where key.paper_id = p_paper_id
      and key.source_sha256 = p_source_sha256
      and key.parser_version = p_parser_version
      and key.question_count = v_count
      and (select count(*) from public.paper_answers answer
           where answer.paper_id = p_paper_id) = v_count
  ) then
    return v_count;
  end if;

  insert into public.paper_answer_keys as key
    (paper_id, source_url, source_sha256, question_count, parsed_at,
     verified_at, parser_version)
  values
    (p_paper_id, p_source_url, p_source_sha256, v_count, now(), now(),
     p_parser_version)
  on conflict (paper_id) do update set
    source_url = excluded.source_url,
    source_sha256 = excluded.source_sha256,
    question_count = excluded.question_count,
    parsed_at = excluded.parsed_at,
    verified_at = excluded.verified_at,
    parser_version = excluded.parser_version;

  delete from public.paper_answers where paper_id = p_paper_id;
  insert into public.paper_answers
    (paper_id, question_number, correct_option, option_count, marks)
  select
    p_paper_id,
    (item->>'question_number')::smallint,
    (item->>'correct_option')::smallint,
    (item->>'option_count')::smallint,
    (item->>'marks')::smallint
  from jsonb_array_elements(p_answers) item;

  -- Re-fire the marking trigger for every retained attempt on this paper.
  update public.question_attempts qa
     set selected_option = qa.selected_option
    from public.exam_attempts ea
   where ea.id = qa.exam_attempt_id
     and ea.paper_id = p_paper_id;

  return v_count;
end;
$$;

create or replace function public.start_exam_attempt(
  p_paper_id text,
  p_client_timezone text default 'UTC'
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid := auth.uid();
  v_timezone text;
  v_question_count smallint;
  v_attempt_id uuid;
begin
  if v_user_id is null then
    raise exception 'authentication required' using errcode = '28000';
  end if;
  select question_count into v_question_count
  from public.paper_answer_keys
  where paper_id = p_paper_id and verified_at is not null;
  if v_question_count is null then
    raise exception 'paper has no verified answer key' using errcode = '55000';
  end if;
  select name into v_timezone from pg_timezone_names where name = p_client_timezone;
  v_timezone := coalesce(v_timezone, 'UTC');

  insert into public.exam_attempts
    (user_id, paper_id, questions_total, client_timezone, local_date)
  values
    (v_user_id, p_paper_id, v_question_count, v_timezone,
     (now() at time zone v_timezone)::date)
  returning id into v_attempt_id;
  return v_attempt_id;
end;
$$;

create or replace function public.finalize_exam_attempt(
  p_attempt_id uuid,
  p_completion_id uuid,
  p_duration_ms integer,
  p_questions jsonb,
  p_events jsonb default '[]'::jsonb
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid := auth.uid();
  v_attempt public.exam_attempts;
  v_question_count integer;
  v_answered integer;
  v_correct integer;
begin
  if v_user_id is null then
    raise exception 'authentication required' using errcode = '28000';
  end if;
  if p_completion_id is null then
    raise exception 'completion id required' using errcode = '22023';
  end if;

  select * into v_attempt from public.exam_attempts
   where id = p_attempt_id and user_id = v_user_id for update;
  if not found then
    raise exception 'attempt not found' using errcode = '42501';
  end if;

  if v_attempt.status = 'completed' and v_attempt.completion_id = p_completion_id then
    select count(*) filter (where is_correct), count(selected_option)
      into v_correct, v_answered
    from public.question_attempts where exam_attempt_id = p_attempt_id;
    return jsonb_build_object(
      'attempt_id', p_attempt_id, 'status', 'completed',
      'questions_correct', v_correct, 'questions_answered', v_answered
    );
  end if;
  if v_attempt.status <> 'in_progress' then
    raise exception 'attempt is already closed' using errcode = '55000';
  end if;
  if jsonb_typeof(p_questions) <> 'array'
     or jsonb_array_length(p_questions) <> v_attempt.questions_total then
    raise exception 'completion must contain every paper question' using errcode = '22023';
  end if;
  if jsonb_typeof(p_events) <> 'array' then
    raise exception 'events must be an array' using errcode = '22023';
  end if;
  select count(distinct (item->>'question_number')::integer)
    into v_question_count from jsonb_array_elements(p_questions) item;
  if v_question_count <> v_attempt.questions_total or exists (
    select 1 from jsonb_array_elements(p_questions) item
    where (item->>'question_number')::integer not between 1 and v_attempt.questions_total
       or coalesce((item->>'selected_option')::integer, 0) < 0
       or coalesce((item->>'time_spent_ms')::integer, 0) < 0
       or coalesce((item->>'confidence')::real, 0) not between 0 and 1
       or coalesce((item->>'difficulty')::real, 0) not between 0 and 1
       or coalesce((item->>'interest')::real, 0) not between 0 and 1
  ) then
    raise exception 'question payload does not match the paper' using errcode = '22023';
  end if;
  if exists (
    select 1
    from jsonb_array_elements(p_questions) item
    join public.paper_answers answer
      on answer.paper_id = v_attempt.paper_id
     and answer.question_number = (item->>'question_number')::smallint
    where item->>'selected_option' is not null
      and (item->>'selected_option')::integer >= answer.option_count
  ) then
    raise exception 'selected option is outside the question bounds' using errcode = '22023';
  end if;
  if exists (
    select 1 from jsonb_array_elements(p_events) with ordinality event(item, ordinal)
    where coalesce((item->>'seq')::integer, ordinal::integer - 1) < 0
       or coalesce((item->>'elapsed_ms')::integer, 0) < 0
       or item->>'question_number' is null
       or (item->>'question_number')::integer not between 1 and v_attempt.questions_total
       or not coalesce((
         (item->>'element_type' = 'highlight' and item->>'action_type' in
           ('setCorrect','deselectedCorrect','setElim','deselectedElim','elimToCorrect','correctToElim'))
         or (item->>'element_type' = 'focusArea' and item->>'action_type' in
           ('userClick','userHoveredIn','userHoveredOutPage'))
         or (item->>'element_type' in ('Copy','Flag','Star','Save') and item->>'action_type' in
           ('Selection','Deselection'))
       ), false)
  ) or (
    select count(*) <> count(distinct coalesce((item->>'seq')::integer, ordinal::integer - 1))
    from jsonb_array_elements(p_events) with ordinality event(item, ordinal)
  ) then
    raise exception 'event payload is invalid' using errcode = '22023';
  end if;

  insert into public.question_attempts
    (exam_attempt_id, question_number, selected_option, eliminated_mask,
     time_spent_ms, hesitation_ms, option_switch_count,
     elimination_reversal_count, revisit_count, marked_for_review_count,
     marked_as_difficult_count, marked_for_save_count,
     stable_elimination_ratio, exploration_depth, exploration_breadth)
  select
    p_attempt_id,
    (item->>'question_number')::smallint,
    (item->>'selected_option')::smallint,
    coalesce((item->>'eliminated_mask')::smallint, 0),
    greatest(coalesce((item->>'time_spent_ms')::integer, 0), 0),
    greatest((item->>'hesitation_ms')::integer, 0),
    greatest(coalesce((item->>'option_switch_count')::smallint, 0), 0),
    greatest(coalesce((item->>'elimination_reversal_count')::smallint, 0), 0),
    greatest(coalesce((item->>'revisit_count')::smallint, 0), 0),
    greatest(coalesce((item->>'marked_for_review_count')::smallint, 0), 0),
    greatest(coalesce((item->>'marked_as_difficult_count')::smallint, 0), 0),
    greatest(coalesce((item->>'marked_for_save_count')::smallint, 0), 0),
    least(greatest(coalesce((item->>'stable_elimination_ratio')::real, 0), 0), 1),
    greatest(coalesce((item->>'exploration_depth')::smallint, 0), 0),
    greatest(coalesce((item->>'exploration_breadth')::smallint, 0), 0)
  from jsonb_array_elements(p_questions) item;

  insert into public.question_metrics
    (question_attempt_id, metrics_version, confidence, difficulty, interest)
  select
    qa.id,
    1,
    least(greatest(coalesce((item->>'confidence')::real, 0), 0), 1),
    least(greatest(coalesce((item->>'difficulty')::real, 0), 0), 1),
    least(greatest(coalesce((item->>'interest')::real, 0), 0), 1)
  from jsonb_array_elements(p_questions) item
  join public.question_attempts qa
    on qa.exam_attempt_id = p_attempt_id
   and qa.question_number = (item->>'question_number')::smallint;

  insert into public.attempt_events
    (exam_attempt_id, seq, question_number, element_type, action_type,
     option_index, elapsed_ms, occurred_at)
  select
    p_attempt_id,
    coalesce((item->>'seq')::integer, ordinal::integer - 1),
    (item->>'question_number')::smallint,
    coalesce(nullif(item->>'element_type', ''), 'unknown'),
    coalesce(nullif(item->>'action_type', ''), 'unknown'),
    (item->>'option_index')::smallint,
    greatest(coalesce((item->>'elapsed_ms')::integer, 0), 0),
    v_attempt.started_at
      + make_interval(secs => greatest(coalesce((item->>'elapsed_ms')::integer, 0), 0) / 1000.0)
  from jsonb_array_elements(p_events) with ordinality as event(item, ordinal);

  select count(selected_option), count(*) filter (where is_correct)
    into v_answered, v_correct
  from public.question_attempts where exam_attempt_id = p_attempt_id;

  update public.exam_attempts set
    status = 'completed',
    completion_id = p_completion_id,
    finished_at = now(),
    duration_ms = greatest(coalesce(p_duration_ms, 0), 0),
    questions_answered = v_answered
  where id = p_attempt_id;

  return jsonb_build_object(
    'attempt_id', p_attempt_id, 'status', 'completed',
    'questions_correct', v_correct, 'questions_answered', v_answered
  );
end;
$$;

create or replace function public.abandon_exam_attempt(
  p_attempt_id uuid,
  p_duration_ms integer default null
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  v_changed integer;
begin
  if auth.uid() is null then
    raise exception 'authentication required' using errcode = '28000';
  end if;
  update public.exam_attempts set
    status = 'abandoned', finished_at = now(),
    duration_ms = greatest(coalesce(p_duration_ms, 0), 0)
  where id = p_attempt_id and user_id = auth.uid() and status = 'in_progress';
  get diagnostics v_changed = row_count;
  return v_changed = 1;
end;
$$;

create or replace function public.record_ide_attempt_trusted(
  p_user_id uuid,
  p_record_id text,
  p_score integer,
  p_max_marks integer,
  p_source text default null,
  p_answer_kind text default null,
  p_points jsonb default null,
  p_client_timezone text default null
) returns public.ide_progress
language plpgsql
security definer
set search_path = public
as $$
declare
  v_timezone text;
  v_score integer := greatest(coalesce(p_score, 0), 0);
  v_max_marks integer := greatest(coalesce(p_max_marks, 0), 0);
  v_solved boolean;
  v_row public.ide_progress;
begin
  if p_user_id is null or p_record_id is null or p_record_id = '' then
    raise exception 'user and record are required' using errcode = '22023';
  end if;
  v_score := least(v_score, v_max_marks);
  v_solved := v_max_marks > 0 and v_score >= v_max_marks;
  select name into v_timezone from pg_timezone_names where name = p_client_timezone;
  v_timezone := coalesce(v_timezone, 'UTC');

  insert into public.ide_attempts
    (user_id, record_id, score, max_marks, answer_kind, source, points,
     local_date, client_timezone)
  values
    (p_user_id, p_record_id, v_score, v_max_marks, p_answer_kind,
     left(p_source, 20000), p_points, (now() at time zone v_timezone)::date,
     v_timezone);

  insert into public.ide_progress as progress
    (user_id, record_id, status, best_score, max_marks, attempts,
     last_source, updated_at)
  values
    (p_user_id, p_record_id,
     case when v_solved then 'solved' else 'attempted' end,
     v_score, v_max_marks, 1, left(p_source, 20000), now())
  on conflict (user_id, record_id) do update set
    status = case when v_solved or progress.status = 'solved'
                  then 'solved' else 'attempted' end,
    best_score = greatest(progress.best_score, excluded.best_score),
    max_marks = excluded.max_marks,
    attempts = progress.attempts + 1,
    last_source = coalesce(excluded.last_source, progress.last_source),
    updated_at = now()
  returning * into v_row;
  return v_row;
end;
$$;

-- Browser roles may read their history, but only narrow functions can create
-- or transition it. Existing owner RLS remains defence in depth for SELECT.
revoke insert, update, delete on public.paper_answer_keys from authenticated;
revoke insert, update, delete on public.paper_answers from authenticated;
revoke insert, update, delete on public.exam_attempts from authenticated;
revoke insert, update, delete on public.question_attempts from authenticated;
revoke insert, update, delete on public.question_metrics from authenticated;
revoke insert, update, delete on public.attempt_events from authenticated;
revoke insert, update, delete on public.ide_progress from authenticated;
revoke insert, update, delete on public.ide_attempts from authenticated;
revoke all on sequence public.ide_attempts_id_seq from authenticated;

revoke all on function public.install_verified_answer_key(text, text, text, integer, jsonb) from public;
grant execute on function public.install_verified_answer_key(text, text, text, integer, jsonb) to service_role;

revoke all on function public.start_exam_attempt(text, text) from public;
grant execute on function public.start_exam_attempt(text, text) to authenticated;
revoke all on function public.finalize_exam_attempt(uuid, uuid, integer, jsonb, jsonb) from public;
grant execute on function public.finalize_exam_attempt(uuid, uuid, integer, jsonb, jsonb) to authenticated;
revoke all on function public.abandon_exam_attempt(uuid, integer) from public;
grant execute on function public.abandon_exam_attempt(uuid, integer) to authenticated;

revoke all on function public.record_ide_attempt_trusted(uuid, text, integer, integer, text, text, jsonb, text) from public;
grant execute on function public.record_ide_attempt_trusted(uuid, text, integer, integer, text, text, jsonb, text) to service_role;
revoke all on function public.record_ide_attempt(text, integer, integer, text, text, jsonb, text) from authenticated;
revoke all on function public.remark_attempt(uuid) from public;
revoke all on function public.set_question_correctness() from public;

revoke all on all sequences in schema public from anon;
revoke all on all sequences in schema public from authenticated;
revoke truncate, references, trigger, maintain on all tables in schema public from anon;
revoke truncate, references, trigger, maintain on all tables in schema public from authenticated;

alter default privileges for role postgres in schema public
  revoke all on tables from anon, authenticated;
alter default privileges for role postgres in schema public
  revoke all on sequences from anon, authenticated;
alter default privileges for role postgres in schema public
  revoke execute on functions from public, anon, authenticated;
