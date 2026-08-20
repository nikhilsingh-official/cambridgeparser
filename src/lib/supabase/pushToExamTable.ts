// this file previously exported a single pushToExamTable() that inserted a
// finished attempt inside endExam(). That meant an abandoned paper was never
// recorded at all, started_at was a client claim made at END time rather than
// an observation, and resume was impossible. It is now a two-phase lifecycle:
// startExamAttempt() at the start, finishExamAttempt() at the end.
// The original single-shot export is kept at the bottom for compatibility.

// typed against the schema mirror in @/lib/types/database, replacing
// `supabase: any` / `session: any`. A misspelled column or a wrong unit is
// now a compile error rather than a Postgres error at runtime.
import type { Session } from '@supabase/supabase-js';
import type {
  Db,
  ExamAttemptFinish,
  ExamAttemptInsert,
  ExamAttemptRow,
} from '@/lib/types/database';
import { AttemptStatus } from '@/lib/types/enums';

// local calendar date in the user's own timezone. "Practice streak" and
// "peak solving hour" are local-calendar ideas; deriving them from a UTC
// timestamp is wrong for anyone not on UTC. Computed here rather than as a
// generated column because `at time zone <column>` is STABLE, not IMMUTABLE,
// so Postgres will not accept it in a generated expression.
function localDateFor(timezone: string, when: Date): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(when);
}

// opens an attempt. Returns the row id, which the caller holds for the rest
// of the exam and passes to every subsequent write.
export async function startExamAttempt(
  supabase: Db,
  props: { schema: string },
  session: Session,
  questionsTotal?: number,
): Promise<string> {
  if (!session?.user?.id) throw new Error('No session user id');

  const now = new Date();
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

  const payload: ExamAttemptInsert = {
    user_id: session.user.id,
    // the Cambridge schema string stays ground truth. subject_code, series,
    // exam_year, paper_number and variant are GENERATED from it in Postgres, so
    // there is nothing extra to send and the two can never disagree.
    paper_id: props.schema,
    status: AttemptStatus.InProgress,
    started_at: now.toISOString(),
    client_timezone: timezone,
    local_date: localDateFor(timezone, now),
  };
  if (typeof questionsTotal === 'number') payload.questions_total = questionsTotal;

  const { data, error } = await supabase
    .from('exam_attempts')
    .insert(payload)
    .select()
    .single();

  if (error) {
    console.error('Failed to open exam_attempt:', error);
    throw error;
  }
  if (!data?.id) throw new Error('No exam_attempt id returned from Supabase');
  return (data as ExamAttemptRow).id;
}

// closes an attempt opened by startExamAttempt().
export async function finishExamAttempt(
  supabase: Db,
  examAttemptId: string,
  totalTimeMs: number | null,
  questionsAnswered: number,
  status: typeof AttemptStatus.Completed | typeof AttemptStatus.Abandoned = AttemptStatus.Completed,
): Promise<void> {
  if (!examAttemptId) throw new Error('examAttemptId required');

  const payload: ExamAttemptFinish = {
    status,
    finished_at: new Date().toISOString(),
    questions_answered: questionsAnswered,
  };
  if (typeof totalTimeMs === 'number') payload.duration_ms = Math.round(totalTimeMs);

  const { error } = await supabase
    .from('exam_attempts')
    .update(payload)
    .eq('id', examAttemptId);

  if (error) {
    console.error('Failed to finish exam_attempt:', error);
    throw error;
  }
}

// kept so any caller still using the old one-shot signature keeps working.
// Prefer startExamAttempt() + finishExamAttempt().
export async function pushToExamTable(
  supabase: Db,
  props: { schema: string },
  session: Session,
  totalTimeMs: number | null,
  _startedIso?: string,
  _finishedAtIso?: string,
): Promise<string> {
  const id = await startExamAttempt(supabase, props, session);
  await finishExamAttempt(supabase, id, totalTimeMs, 0);
  return id;
}
