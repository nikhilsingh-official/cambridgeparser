// ==========================================================================
//
// Converts the extractor's PDF-shaped rows into the narrow database contract.
// Returning null is intentional: an incomplete key makes the paper practice-
// only instead of persisting a confidently wrong score.
// ==========================================================================

import type { AnswerTableRow } from './answerKey.ts';

export interface TrustedAnswerRow {
  question_number: number;
  correct_option: number;
  option_count: number;
  marks: number;
}

export function normalizeTrustedAnswerKey(
  answers: AnswerTableRow[] | null,
): TrustedAnswerRow[] | null {
  if (!answers?.length) return null;

  const rows: TrustedAnswerRow[] = [];
  for (let index = 0; index < answers.length; index += 1) {
    const answer = answers[index]!;
    const letter = answer.answer.trim().toUpperCase();
    const correctOption = letter.length === 1 ? letter.charCodeAt(0) - 65 : -1;
    const marks = Number.parseInt(answer.marks, 10);
    if (
      answer.question !== index + 1
      || correctOption < 0
      || correctOption > 3
      || !Number.isInteger(marks)
      || marks < 1
    ) return null;

    rows.push({
      question_number: answer.question,
      correct_option: correctOption,
      option_count: 4,
      marks,
    });
  }
  return rows;
}

export async function sha256Hex(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}
