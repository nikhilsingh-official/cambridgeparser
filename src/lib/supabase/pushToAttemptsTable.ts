import type { QuestionsAnalytics } from "../processing/processingTypes";
import { lettersToMask } from "./lettersToMask";
import { letterToIndex } from "./letterToIndex";

export async function pushToAttemptsTable(supabase: any, examAttemptId: string, enrichedData: QuestionsAnalytics) {
  if (!examAttemptId) throw new Error('examAttemptId required');
  if (!Array.isArray(enrichedData)) throw new Error('enrichedData must be an array');

  const payload = enrichedData.map(q => ({
    exam_attempt_id: examAttemptId,
    question_number: q.questionNumber,

    selected_option: letterToIndex(q.selectedOption),
    eliminated_options_mask: lettersToMask(q.eliminatedOptions),

    time_spent_ms: Math.round(q.time ?? 0),

    marked_for_review_count: q.markedForReview ? 1 : 0,
    marked_as_difficult_count: q.markedAsDifficult ? 1 : 0,
    marked_for_save_count: q.markedForSave ? 1 : 0,

    hesitation_time_ms: q.hesitationTime ?? null,
    option_switch_count: q.optionSwitchCount ?? 0,
    elimination_reversal_count: q.eliminationReversalCount ?? 0,
    revisit_count: q.revisitCount ?? 0,

    stable_elimination_ratio: q.stableEliminationRatio ?? 0,
    exploration_depth: q.explorationDepth ?? 0,
    exploration_breadth: q.explorationBreadth ?? 0,

    confidence: q.confidenceScore ?? 0,
    difficulty: q.difficultyScore ?? 0,
    interest: q.interestScore ?? 0,
  }));

  const { data, error } = await supabase
    .from('question_attempts')
    .upsert(payload, { onConflict: 'exam_attempt_id,question_number' })
    .select();

  if (error) {
    console.error('Failed to insert/upsert question_attempts:', error);
    throw error;
  }

  return data;
}