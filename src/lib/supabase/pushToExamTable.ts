// this file previously exported a single pushToExamTable() that inserted a
// finished attempt inside endExam(). That meant an abandoned paper was never
// recorded at all, started_at was a client claim made at END time rather than
// an observation, and resume was impossible. It is now an RPC lifecycle:
// startExamAttempt() at the start, finalizeExamAttempt() or
// abandonExamAttempt() at the end.
// Completion is deliberately unavailable through a one-shot compatibility
// helper: it requires the full question/event payload and an idempotency key.

// typed against the schema mirror in @/lib/types/database, replacing
// `supabase: any` / `session: any`. A misspelled column or a wrong unit is
// now a compile error rather than a Postgres error at runtime.
import type { Session } from '@supabase/supabase-js';
import type { Db } from '@/lib/types/database';
// completion now crosses one transactional RPC boundary instead of four
// table writers. These imports shape the browser telemetry for that boundary.
import type { QuestionsAnalytics } from '@/lib/processing/processingTypes';
import type { EventLogs } from '@/lib/utils/utilsTypes';
import { letterToIndex } from './letterToIndex';
import { lettersToMask } from './lettersToMask';
import { EventElement } from '@/lib/types/enums';

// opens an attempt. Returns the row id, which the caller holds for the rest
// of the exam and passes to every subsequent write.
export async function startExamAttempt(
  supabase: Db,
  props: { schema: string },
  session: Session,
  questionsTotal?: number,
): Promise<string> {
  if (!session?.user?.id) throw new Error('No session user id');

  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  void questionsTotal;
  const { data, error } = await supabase.rpc('start_exam_attempt', {
    p_paper_id: props.schema,
    p_client_timezone: timezone,
  });

  if (error) {
    console.error('Failed to open exam_attempt:', error);
    throw error;
  }
  if (typeof data !== 'string') throw new Error('No exam_attempt id returned from Supabase');
  return data;
}

// marks an unfinished attempt abandoned.
export async function abandonExamAttempt(
  supabase: Db,
  examAttemptId: string,
  totalTimeMs: number | null,
): Promise<void> {
  if (!examAttemptId) throw new Error('examAttemptId required');

  const { error } = await supabase.rpc('abandon_exam_attempt', {
    p_attempt_id: examAttemptId,
    p_duration_ms: typeof totalTimeMs === 'number' ? Math.round(totalTimeMs) : null,
  });

  if (error) {
    console.error('Failed to abandon exam_attempt:', error);
    throw error;
  }
}

// one public persistence seam for a completed solver attempt. Postgres
// validates the paper shape, calculates correctness and commits every row.
export async function finalizeExamAttempt(
  supabase: Db,
  examAttemptId: string,
  completionId: string,
  totalTimeMs: number,
  questions: QuestionsAnalytics,
  eventLogs: EventLogs,
): Promise<void> {
  const questionPayload = questions.map(question => ({
    question_number: question.questionNumber,
    selected_option: letterToIndex(question.selectedOption),
    eliminated_mask: lettersToMask(question.eliminatedOptions),
    time_spent_ms: Math.round((question.time ?? 0) * 1000),
    hesitation_ms: question.hesitationTime ?? null,
    option_switch_count: question.optionSwitchCount ?? 0,
    elimination_reversal_count: question.eliminationReversalCount ?? 0,
    revisit_count: question.revisitCount ?? 0,
    marked_for_review_count: question.markedForReview ?? 0,
    marked_as_difficult_count: question.markedAsDifficult ?? 0,
    marked_for_save_count: question.markedForSave ?? 0,
    stable_elimination_ratio: question.stableEliminationRatio ?? 0,
    exploration_depth: question.explorationDepth ?? 0,
    exploration_breadth: question.explorationBreadth ?? 0,
    confidence: question.confidenceScore ?? 0,
    difficulty: question.difficultyScore ?? 0,
    interest: question.interestScore ?? 0,
  }));
  const eventPayload = eventLogs.map((event, index) => ({
    seq: event.seq ?? index,
    question_number: event.question,
    element_type: event.elementType,
    action_type: event.actionType,
    option_index: event.elementType === EventElement.Highlight ? event.option : null,
    elapsed_ms: event.elapsedMs ?? 0,
  }));

  const { error } = await supabase.rpc('finalize_exam_attempt', {
    p_attempt_id: examAttemptId,
    p_completion_id: completionId,
    p_duration_ms: Math.round(totalTimeMs),
    p_questions: questionPayload,
    p_events: eventPayload,
  });
  if (error) {
    console.error('Failed to finalize exam attempt:', error);
    throw error;
  }
}
