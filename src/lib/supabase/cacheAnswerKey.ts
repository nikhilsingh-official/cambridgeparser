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
// NOTE ON TRUST: this writes from the client, so the key is only as
// trustworthy as the browser that sent it. Moving the write into the edge
// function (which already parses the key server-side) is roadmap B4 and is a
// prerequisite for any shared/class view.
//
// Until then, both writes are INSERT ... ON CONFLICT DO NOTHING rather than
// upsert. That matters more than it looks:
//
//   paper_answers is keyed by PAPER, not by user - one row set serves everyone
//   who ever sits that paper. An upsert let any client REWRITE a key that was
//   already cached, and the set_question_correctness trigger would then dutifully
//   re-mark against it. So a single bad client could not merely flatter its own
//   score, it could corrupt every other student's marks for that paper.
//
// Insert-if-absent makes the cached key immutable from the browser: first
// writer wins, and the only way to correct a mis-parse is server-side. It also
// removes a pointless write - a mark scheme does not change between sittings,
// so re-sending it on every attempt was work with no effect.
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

  // `ignoreDuplicates: true` sends `Prefer: resolution=ignore-duplicates`,
  // which PostgREST turns into `on conflict do nothing`. That needs only the
  // INSERT privilege. The previous call omitted it, so PostgREST emitted
  // `on conflict do update` - which needs UPDATE, and UPDATE is precisely the
  // privilege that let one client overwrite everybody's answer key.
  //
  // A plain .insert() would NOT do: it emits a bare INSERT and would fail with
  // a duplicate-key error the second time anyone sits the same paper.
  const { error: keyError } = await supabase
    .from('paper_answer_keys')
    .upsert(
      {
        paper_id: paperId,
        source_url: sourceUrl ?? null,
        question_count: answers.length,
        parsed_at: new Date().toISOString(),
      },
      { onConflict: 'paper_id', ignoreDuplicates: true },
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
    .upsert(rows, {
      onConflict: 'paper_id,question_number',
      ignoreDuplicates: true,
    });
  if (error) {
    console.error('Failed to upsert paper_answers:', error);
    throw error;
  }
  return rows.length;
}
