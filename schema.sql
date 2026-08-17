create extension if not exists pgcrypto;


create table if not exists attempts (

  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references auth.users(id) on delete cascade,

  attempt_type text not null,

  metadata jsonb default '{}'::jsonb,

  created_at timestamptz not null default now()

);


create index if not exists idx_attempts_user on attempts(user_id);


create table if not exists exam_attempts (

  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references auth.users(id) on delete cascade,

  paper_id text,

  started_at timestamptz default now(),

  finished_at timestamptz,

  total_time_ms integer,

  created_at timestamptz not null default now()

);


create index if not exists idx_exam_attempts_user_finished on exam_attempts(user_id, finished_at);

create index if not exists idx_exam_attempts_user on exam_attempts(user_id);


create table if not exists question_attempts (

  id uuid primary key default gen_random_uuid(),

  exam_attempt_id uuid not null references exam_attempts(id) on delete cascade,

  question_number integer not null,


  selected_option smallint check (selected_option between 0 and 3),


  eliminated_options_mask smallint default 0 check (eliminated_options_mask between 0 and 15),


  time_spent_ms integer not null default 0,

  marked_for_review_count integer not null default 0,

  marked_as_difficult_count integer not null default 0,

  marked_for_save_count integer not null default 0,


  hesitation_time_ms integer,

  option_switch_count smallint default 0,

  elimination_reversal_count smallint default 0,

  revisit_count smallint default 0,


  stable_elimination_ratio real default 0,

  exploration_depth integer default 0,

  exploration_breadth integer default 0,


  confidence real default 0,

  difficulty real default 0,

  interest real default 0,


  created_at timestamptz not null default now(),


  constraint uq_exam_question unique (exam_attempt_id, question_number)

);


create index if not exists idx_question_attempts_question on question_attempts(question_number);

create index if not exists idx_question_attempts_exam on question_attempts(exam_attempt_id);
