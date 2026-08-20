import type { QuestionsAnalytics } from "../processing/processingTypes";
// typed against the schema mirror. QuestionAttemptInsert deliberately
// omits is_correct, so an attempt to send it will not compile.
import type {
  Db,
  QuestionAttemptInsert,
  QuestionAttemptRef,
  QuestionMetricsInsert,
} from "@/lib/types/database";
import { lettersToMask } from "./lettersToMask";
import { letterToIndex } from "./letterToIndex";

// QuestionAnalytics.time is accumulated in SECONDS by
// src/lib/focusAreas/startFocusAreaTimer.ts (`active.time += deltaSeconds`).
// It was previously written straight into the column named time_spent_ms, so
// that column held seconds while hesitation_time_ms and total_time_ms held real
// milliseconds - two `_ms` columns in one schema differing by 1000x.
// The conversion happens here, at the boundary, so the in-memory model is
// untouched and the stored unit finally matches the column name.
const SECONDS_TO_MS = 1000;

export async function pushToAttemptsTable(supabase: Db, examAttemptId: string, enrichedData: QuestionsAnalytics): Promise<QuestionAttemptRef[]> {
  if (!examAttemptId) throw new Error('examAttemptId required');
  if (!Array.isArray(enrichedData)) throw new Error('enrichedData must be an array');

  const payload: QuestionAttemptInsert[] = enrichedData.map(q => ({
    exam_attempt_id: examAttemptId,
    question_number: q.questionNumber,

    selected_option: letterToIndex(q.selectedOption),
    // renamed from eliminated_options_mask to match the new schema.
    eliminated_mask: lettersToMask(q.eliminatedOptions),

    // seconds -> milliseconds. Was `Math.round(q.time ?? 0)`.
    time_spent_ms: Math.round((q.time ?? 0) * SECONDS_TO_MS),

    // these were `q.markedForReview ? 1 : 0`, which collapsed a real count
    // into a 0/1 flag - three columns named `_count` that could never hold a
    // count. enrichAnalytics already produces true counts (flagCount,
    // difficultCount, saveCount), so pass them through.
    marked_for_review_count: q.markedForReview ?? 0,
    marked_as_difficult_count: q.markedAsDifficult ?? 0,
    marked_for_save_count: q.markedForSave ?? 0,

    // renamed from hesitation_time_ms to match the new schema. Already ms
    // (it comes from performance.now() differences), so no conversion.
    hesitation_ms: q.hesitationTime ?? null,
    option_switch_count: q.optionSwitchCount ?? 0,
    elimination_reversal_count: q.eliminationReversalCount ?? 0,
    revisit_count: q.revisitCount ?? 0,

    stable_elimination_ratio: q.stableEliminationRatio ?? 0,
    exploration_depth: q.explorationDepth ?? 0,
    exploration_breadth: q.explorationBreadth ?? 0,

    // is_correct is deliberately NOT sent. It is set by the
    // set_question_correctness() trigger from the cached answer key, so the
    // browser cannot assert its own score. confidence/difficulty/interest have
    // moved to question_metrics (they are weight-dependent and versioned) and
    // are written by pushQuestionMetrics().
  }));

  const { data, error } = await supabase
    .from('question_attempts')
    .upsert(payload, { onConflict: 'exam_attempt_id,question_number' })
    .select();

  if (error) {
    console.error('Failed to insert/upsert question_attempts:', error);
    throw error;
  }

  return (data ?? []) as QuestionAttemptRef[];
}

// new. The three weighted composites now live in their own versioned table,
// because they depend on tunable weights AND on cross-question normalisation
// (meanTime/meanNorm/stdNorm across the whole paper) - so they are not
// properties of a single response and they change when the formula changes.
// `rows` is what pushToAttemptsTable() returned, so ids line up by question.
export async function pushQuestionMetrics(
  supabase: Db,
  insertedRows: QuestionAttemptRef[],
  enrichedData: QuestionsAnalytics,
  metricsVersion = 1,
) {
  if (!Array.isArray(insertedRows) || insertedRows.length === 0) return [];

  const idByQuestion = new Map(insertedRows.map(r => [r.question_number, r.id]));

  const payload: QuestionMetricsInsert[] = enrichedData
    .filter(q => idByQuestion.has(q.questionNumber))
    .map(q => ({
      // non-null asserted - the .filter() above already proved the key is
      // present, which Map.get()'s signature cannot express.
      question_attempt_id: idByQuestion.get(q.questionNumber)!,
      metrics_version: metricsVersion,
      confidence: q.confidenceScore ?? 0,
      difficulty: q.difficultyScore ?? 0,
      interest: q.interestScore ?? 0,
    }));

  if (payload.length === 0) return [];

  const { data, error } = await supabase
    .from('question_metrics')
    .upsert(payload, { onConflict: 'question_attempt_id,metrics_version' })
    .select();

  if (error) {
    console.error('Failed to insert/upsert question_metrics:', error);
    throw error;
  }
  return data;
}
