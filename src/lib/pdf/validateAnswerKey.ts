// ============================================================================
// ============================================================================

import type { TableRow } from '@/lib/processing/processingTypes';

/**
 * Validate and normalize the untrusted JSON returned by fetch-pdf.
 *
 * A partial key is worse than no key: downstream code otherwise treats a
 * missing row as a wrong answer worth one mark. Requiring a contiguous sequence
 * makes the boundary fail closed instead of publishing a plausible wrong score.
 */
export function validateAnswerKey(value: unknown): TableRow[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;

  const rows: TableRow[] = [];

  for (let index = 0; index < value.length; index++) {
    const raw = value[index];
    if (!raw || typeof raw !== 'object') return null;

    const candidate = raw as Record<string, unknown>;
    const question = candidate.question;
    const answer = typeof candidate.answer === 'string'
      ? candidate.answer.trim().toUpperCase()
      : '';
    const marksText = String(candidate.marks ?? '').trim();
    const page = candidate.page;
    const y = candidate.y;

    if (question !== index + 1) return null;
    if (!/^[A-D]$/.test(answer)) return null;
    if (!/^\d+$/.test(marksText) || Number.parseInt(marksText, 10) <= 0) return null;
    if (!Number.isInteger(page) || (page as number) < 1) return null;
    if (typeof y !== 'number' || !Number.isFinite(y)) return null;

    rows.push({
      question,
      answer,
      marks: marksText,
      page: page as number,
      y,
    });
  }

  return rows;
}
