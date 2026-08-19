-- ==========================================================================
--
-- Synthetic data so the stats page is worth looking at in local development.
--
-- WHY THIS EXISTS: every chart on the stats page is a function of data that
-- does not exist until someone has sat a dozen papers. Building or reviewing
-- those charts against an empty database means building them blind, and an
-- empty chart looks identical to a broken one.
--
-- WHERE IT RUNS: `supabase db reset` only. `supabase db push` - the way a
-- hosted project is migrated - does not run seeds, so this cannot reach
-- production by the normal deploy path. It is still guarded below.
--
-- WHAT IT IS NOT: a fixture for automated tests. Tests that assert on numbers
-- should build their own rows; the shape here is deliberately irregular so the
-- charts look like a person's revision history rather than a sine wave.
-- ==========================================================================

-- Refuse to run anywhere that already has real accounts. The dev user below is
-- the only account a local stack should have; if there are others, this is not
-- a throwaway database and inventing 1800 question attempts in it would be
-- vandalism.
do $$
declare
  outsiders integer;
begin
  select count(*) into outsiders
  from auth.users
  where email is distinct from 'dev@local.test';

  if outsiders > 0 then
    raise notice 'skipping dev sample data: % non-dev account(s) present', outsiders;
    return;
  end if;

  -- ------------------------------------------------------------------ user
  -- The token columns must be '' and never NULL. GoTrue scans them into Go
  -- strings, and a NULL fails the scan with
  --   "converting NULL to string is unsupported"
  -- which surfaces as a 500 from /auth/v1/token - i.e. the seeded account
  -- exists, looks correct in the table, and cannot log in. Learned the hard
  -- way; do not "tidy" these into NULLs.
  insert into auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, created_at, updated_at,
    raw_app_meta_data, raw_user_meta_data,
    confirmation_token, recovery_token, email_change_token_new, email_change,
    phone_change, phone_change_token, email_change_token_current,
    reauthentication_token
  ) values (
    '00000000-0000-4000-8000-000000000001',
    '00000000-0000-0000-0000-000000000000',
    'authenticated', 'authenticated', 'dev@local.test',
    -- bcrypt of 'devpassword123'
    crypt('devpassword123', gen_salt('bf')),
    now(), now() - interval '150 days', now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{}'::jsonb,
    '', '', '', '', '', '', '', ''
  )
  on conflict (id) do nothing;

  insert into auth.identities (
    id, user_id, provider_id, provider, identity_data, created_at, updated_at
  ) values (
    gen_random_uuid(),
    '00000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000001',
    'email',
    '{"sub":"00000000-0000-4000-8000-000000000001","email":"dev@local.test","email_verified":true}'::jsonb,
    now() - interval '150 days', now()
  )
  on conflict do nothing;

  raise notice 'dev sample data: seeding for dev@local.test / devpassword123';
end $$;

-- Everything below is a no-op when the guard above skipped, because the papers
-- CTE joins against the dev user that would not exist.
do $$
declare
  dev_user constant uuid := '00000000-0000-4000-8000-000000000001';
  -- (paper_id, questions). Real Cambridge codes so the join to `subjects`
  -- resolves and the subject filter has recognisable names.
  papers text[] := array[
    '0620_s24_12', '0620_w24_11', '0610_s24_11', '0610_w24_12',
    '0625_s24_13', '0625_w24_11', '0580_s24_12', '0478_s24_11',
    '0478_w24_12', '9618_s24_11'
  ];
  paper text;
  q integer;
  attempt_no integer;
  attempts_total constant integer := 46;
  att_id uuid;
  qa_id uuid;
  started timestamptz;
  day_offset integer;
  -- Ability climbs from ~0.55 to ~0.86 over the period, with noise, so the
  -- trend lines have a real slope to render rather than a flat band.
  skill numeric;
  correct boolean;
  guessed boolean;
  chosen smallint;
  key_opt smallint;
  spent integer;
  conf numeric;
  answered integer;
  qcount constant integer := 40;
begin
  if not exists (select 1 from auth.users where id = dev_user) then
    return;
  end if;

  -- --------------------------------------------------------------- answers
  -- One answer key per paper. Deterministic so a reset reproduces the same
  -- database: a seed whose numbers move under you is a debugging trap.
  foreach paper in array papers loop
    insert into paper_answer_keys (paper_id, source_url, question_count, parsed_at)
    values (paper, 'seed://dev-sample-data', qcount, now())
    on conflict (paper_id) do nothing;

    for q in 1..qcount loop
      insert into paper_answers (paper_id, question_number, correct_option, option_count, marks)
      values (paper, q, (abs(hashtext(paper || ':' || q)) % 4)::smallint, 4, 1)
      on conflict (paper_id, question_number) do nothing;
    end loop;
  end loop;

  -- --------------------------------------------------------------- attempts
  for attempt_no in 1..attempts_total loop
    paper := papers[1 + (attempt_no % array_length(papers, 1))];

    -- Spread over ~21 weeks, clustered rather than evenly spaced: roughly
    -- weekly early on, a nine-day gap either side of the middle block, then a
    -- run of twelve consecutive days ending today, so the streak counter has
    -- something to find and the heatmap is not a uniform wash.
    --
    -- Every branch must stay >= 0. An offset that goes negative dates an
    -- attempt in the future, which is silently wrong: the charts still render,
    -- they just show revision that has not happened yet.
    day_offset := case
      when attempt_no <= 20 then 150 - ((attempt_no - 1) * 5)   -- 150 .. 55
      when attempt_no <= 34 then  46 - ((attempt_no - 21) * 2)  --  46 .. 20
      else                        11 -  (attempt_no - 35)       --  11 ..  0
    end;
    if day_offset < 0 then
      raise exception 'seed bug: attempt % produced a negative day offset (%)',
        attempt_no, day_offset;
    end if;
    started := (now()::date - day_offset)
             + make_interval(hours => 15 + (attempt_no % 6), mins => (attempt_no * 7) % 60);

    skill := least(0.88, 0.54 + (attempt_no::numeric / attempts_total) * 0.30)
           + ((abs(hashtext('noise' || attempt_no)) % 11) - 5)::numeric / 100;

    insert into exam_attempts (
      user_id, paper_id, status, started_at, finished_at, duration_ms,
      questions_total, questions_answered, client_timezone, local_date, metrics_version
    ) values (
      dev_user, paper, 'completed', started,
      started + make_interval(mins => 38 + (attempt_no % 17)),
      (38 + (attempt_no % 17)) * 60000,
      qcount, qcount, 'Europe/London', started::date, 1
    )
    returning id into att_id;

    answered := 0;
    for q in 1..qcount loop
      select correct_option into key_opt
        from paper_answers where paper_id = paper and question_number = q;

      correct := (abs(hashtext(att_id::text || ':' || q)) % 100) < (skill * 100);

      -- A few questions per paper are left blank, more often late in the paper
      -- where someone ran short of time.
      if q > 34 and (abs(hashtext('blank' || att_id::text || q)) % 100) < 12 then
        chosen := null;
      elsif correct then
        chosen := key_opt;
        answered := answered + 1;
      else
        chosen := ((key_opt + 1 + (abs(hashtext('wrong' || att_id::text || q)) % 3)) % 4)::smallint;
        answered := answered + 1;
      end if;

      -- v_question_flags calls a question a guess when it was answered fast,
      -- with no eliminations and shallow exploration. Decide that FIRST, then
      -- make the timing and the elimination mask agree with it - otherwise the
      -- flag and the behaviour it is supposed to describe drift apart.
      --
      -- Crucially, a guess must be able to be RIGHT. A first version only ever
      -- made wrong answers fast, so all 101 guesses were wrong and the "guess
      -- accuracy" tile read a confident 0% - a number that looked like a
      -- finding and was really an artefact of the generator. On four options,
      -- luck should land somewhere in the 25-35% band.
      --
      -- The two rates are not symmetric and cannot be read off the target
      -- directly: correct answers outnumber wrong ones roughly 2:1, so equal
      -- rates would make most guesses correct. At 6% of correct answers and
      -- 30% of wrong ones the flagged guesses come out ~30% right, which is
      -- what random-on-four-options looks like once the heuristic's own bias
      -- is included. A first attempt at 9/26 produced 44%.
      guessed := chosen is not null
                 and (abs(hashtext('g' || att_id::text || q)) % 100) < (case when correct then 6 else 30 end);

      spent := case
        when chosen is null then 4000 + (abs(hashtext('t0' || att_id::text || q)) % 6000)
        when guessed then 4000 + (abs(hashtext('t2' || att_id::text || q)) % 6000)
        when correct then 28000 + (abs(hashtext('t1' || att_id::text || q)) % 40000)
        else 45000 + (abs(hashtext('t3' || att_id::text || q)) % 70000)
      end;

      insert into question_attempts (
        exam_attempt_id, question_number, selected_option, eliminated_mask,
        time_spent_ms, hesitation_ms, option_switch_count,
        elimination_reversal_count, revisit_count,
        marked_for_review_count, marked_as_difficult_count, marked_for_save_count,
        stable_elimination_ratio, exploration_depth, exploration_breadth
      ) values (
        att_id, q,
        chosen,
        -- A guess by definition eliminated nothing.
        case when guessed then 0::smallint
             when correct then (abs(hashtext('e' || att_id::text || q)) % 8)::smallint
             else 0::smallint end,
        spent,
        (abs(hashtext('h' || att_id::text || q)) % 9000),
        (abs(hashtext('s' || att_id::text || q)) % 3)::smallint,
        (abs(hashtext('r' || att_id::text || q)) % 2)::smallint,
        (abs(hashtext('v' || att_id::text || q)) % 3)::smallint,
        (case when (abs(hashtext('mr' || att_id::text || q)) % 100) < 8 then 1 else 0 end)::smallint,
        (case when (abs(hashtext('md' || att_id::text || q)) % 100) < 6 then 1 else 0 end)::smallint,
        (case when (abs(hashtext('ms' || att_id::text || q)) % 100) < 4 then 1 else 0 end)::smallint,
        ((abs(hashtext('ser' || att_id::text || q)) % 100) / 100.0)::real,
        -- ... and explored at most one option before committing.
        case when guessed then (abs(hashtext('ed' || att_id::text || q)) % 2)::smallint
             else (abs(hashtext('ed' || att_id::text || q)) % 4)::smallint end,
        (abs(hashtext('eb' || att_id::text || q)) % 4)::smallint
      )
      returning id into qa_id;

      -- Confidence tracks correctness but imperfectly. The two distributions
      -- must OVERLAP: an earlier version drew correct answers from 0.55-0.99
      -- and wrong ones from 0.30-0.74, which separated them completely, so
      -- every confidence bucket below 0.55 was 0% accurate and every bucket
      -- above 0.75 was 100% - a calibration curve with a cliff in it instead of
      -- a curve, and literally zero underconfident questions, because being
      -- right while unsure had been made impossible.
      --
      -- Correct: 0.25-0.94. Wrong: 0.15-0.85. The shared 0.25-0.85 band gives
      -- the middle buckets mixed outcomes.
      --
      -- The lower bound on the correct branch matters more than it looks.
      -- v_question_flags calls a question underconfident when confidence <= 0.4
      -- AND the answer was right, so if correct answers never drop below 0.4
      -- that flag can never fire and the focus section reports a flat zero
      -- forever. A first pass started them at exactly 0.40 and produced zero
      -- underconfident questions out of 1840.
      conf := case when correct
                   then 0.25 + ((abs(hashtext('c' || qa_id::text)) % 70)::numeric / 100)
                   else 0.15 + ((abs(hashtext('c' || qa_id::text)) % 71)::numeric / 100)
              end;
      conf := least(0.99, greatest(0.02, conf));

      insert into question_metrics (question_attempt_id, metrics_version, confidence, difficulty, interest, computed_at)
      values (
        qa_id, 1, conf::real,
        least(0.99, greatest(0.01, 1.0 - conf + ((abs(hashtext('d' || qa_id::text)) % 20)::numeric / 100 - 0.1)))::real,
        ((abs(hashtext('i' || qa_id::text)) % 100) / 100.0)::real,
        started
      );
    end loop;

    update exam_attempts set questions_answered = answered where id = att_id;
  end loop;

  raise notice 'dev sample data: % attempts, % question attempts',
    attempts_total, attempts_total * qcount;
end $$;
