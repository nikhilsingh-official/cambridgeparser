// ==========================================================================
//
// Caches the mark-scheme answer key into paper_answer_keys / paper_answers.
//
// The key is parsed out of the mark-scheme PDF by the fetch-pdf edge function
// on every single attempt and then discarded once grading has run in memory.
// Caching it does four things:
//   - lets the database decide correctness (set_question_correctness trigger),
//     so the browser can no longer assert its own score;
//   - makes re-marking possible after a mis-parsed key is corrected;
//   - stops every attempt re-downloading and re-parsing the mark scheme;
//   - keeps past attempts interpretable if the upstream source disappears.
//
// NOTE ON TRUST: this writes from the client, so for now the key is only as
// trustworthy as the browser that sent it. That is fine for single-user
// self-study and is the smallest change that unblocks correctness. Moving the
// write into the edge function (which already parses the key server-side) is
// tracked in FUTURE_WORK.md and is a prerequisite for any shared/class view.
// ==========================================================================

import type { TableRow } from "@/lib/processing/processingTypes";
import { letterToIndex } from "./letterToIndex";
// typed against the schema mirror, replacing `supabase: any`.
import type { Db, PaperAnswerInsert } from "@/lib/types/database";
import type { OptionLetter } from "@/lib/processing/processingTypes";

export async function cacheAnswerKey(
  supabase: Db,
  paperId: string,
  answers: TableRow[] | null,
  sourceUrl?: string,
): Promise<number> {
  if (!paperId) throw new Error('paperId required');
  if (!Array.isArray(answers) || answers.length === 0) return 0;

  const { error: keyError } = await supabase
    .from('paper_answer_keys')
    .upsert(
      {
        paper_id: paperId,
        source_url: sourceUrl ?? null,
        question_count: answers.length,
        parsed_at: new Date().toISOString(),
      },
      { onConflict: 'paper_id' },
    );
  if (keyError) {
    console.error('Failed to upsert paper_answer_keys:', keyError);
    throw keyError;
  }

  const rows = answers
    .map((a): PaperAnswerInsert | null => {
      const optionIndex = letterToIndex(String(a.answer).trim().toUpperCase() as OptionLetter);
      if (optionIndex === null) return null;
      const marks = Number.parseInt(String(a.marks), 10);
      return {
        paper_id: paperId,
        question_number: a.question,
        correct_option: optionIndex,
        option_count: 4,
        marks: Number.isFinite(marks) && marks > 0 ? marks : 1,
      };
    })
    .filter((r): r is PaperAnswerInsert => r !== null);

  if (rows.length === 0) return 0;

  const { error } = await supabase
    .from('paper_answers')
    .upsert(rows, { onConflict: 'paper_id,question_number' });
  if (error) {
    console.error('Failed to upsert paper_answers:', error);
    throw error;
  }
  return rows.length;
}
