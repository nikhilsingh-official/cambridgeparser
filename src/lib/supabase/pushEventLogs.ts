// ==========================================================================
//
// Persists the raw interaction stream to attempt_events.
//
// This stream was previously built up in memory for the whole exam and then
// thrown away at endExam(), leaving only the scalar aggregates. That is what
// made metric retuning unrecoverable: the weights in enrichAnalytics.ts are
// estimates, and once they change, old rows computed under the old weights are
// no longer comparable to new ones - with the inputs gone there is no way to
// recompute or even detect it.
//
// It is also the only place the *type* of each answer change is recorded.
// selectOption.ts already distinguishes setCorrect / elimToCorrect /
// correctToElim / deselectedCorrect / setElim / deselectedElim along with the
// option index, but enrichAnalytics collapses all of that into a single
// optionSwitchCount. Keeping the stream is what makes answer-change analysis
// ("when you switch, do you switch to the right answer?") possible at all.
//
// Volume: ~200 rows per paper at ~40 bytes each.
// ==========================================================================

import type { EventLogs } from "@/lib/utils/utilsTypes";

const CHUNK_SIZE = 500;

export async function pushEventLogs(
  supabase: any,
  examAttemptId: string,
  eventLogs: EventLogs,
) {
  if (!examAttemptId) throw new Error('examAttemptId required');
  if (!Array.isArray(eventLogs) || eventLogs.length === 0) return 0;

  const payload = eventLogs.map((e, index) => ({
    exam_attempt_id: examAttemptId,
    // Fall back to array position if setEventEpoch() was never called, so a
    // missing epoch degrades to "still ordered" rather than "rejected".
    seq: e.seq ?? index,
    question_number: e.question ?? null,
    element_type: e.elementType,
    action_type: e.actionType,
    option_index: e.option ?? null,
    elapsed_ms: e.elapsedMs ?? 0,
    occurred_at: e.dateTimestamp,
  }));

  let written = 0;
  for (let i = 0; i < payload.length; i += CHUNK_SIZE) {
    const chunk = payload.slice(i, i + CHUNK_SIZE);
    const { error } = await supabase
      .from('attempt_events')
      .upsert(chunk, { onConflict: 'exam_attempt_id,seq' });
    if (error) {
      console.error('Failed to insert attempt_events:', error);
      throw error;
    }
    written += chunk.length;
  }
  return written;
}
