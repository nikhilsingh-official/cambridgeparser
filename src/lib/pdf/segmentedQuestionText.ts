// ============================================================================
// ============================================================================

import type { QuestionSegment, SegmentedQuestions, textbox as Textbox } from './pdfTypes.ts';

const visualLineTolerance = 3;

export interface SegmentedQuestionLocation {
  pageIndex: number;
  segmentIndex: number;
  segment: QuestionSegment;
}

/** Resolve the one-based question number used throughout the solver. */
function findSegmentedQuestion(
  questions: SegmentedQuestions,
  questionNumber: number,
): SegmentedQuestionLocation | null {
  if (!Number.isInteger(questionNumber) || questionNumber < 1) return null;
  let current = 0;
  for (let pageIndex = 0; pageIndex < questions.length; pageIndex++) {
    const page = questions[pageIndex] ?? [];
    for (let segmentIndex = 0; segmentIndex < page.length; segmentIndex++) {
      current++;
      const segment = page[segmentIndex];
      if (current === questionNumber && segment) {
        return { pageIndex, segmentIndex, segment };
      }
    }
  }
  return null;
}

function visualOrder(a: Textbox, b: Textbox): number {
  if (Math.abs(a.y - b.y) > visualLineTolerance) return a.y - b.y;
  return a.x - b.x;
}

/** Produce readable clipboard text without mutating parser stream order. */
export function segmentedQuestionText(
  questions: SegmentedQuestions,
  questionNumber: number,
): string | null {
  const location = findSegmentedQuestion(questions, questionNumber);
  if (!location) return null;

  const items = [...location.segment.segmentText]
    .filter((item) => item.text.trim().length > 0)
    .sort(visualOrder);
  if (items.length === 0) return null;

  const lines: { y: number; text: string[] }[] = [];
  for (const item of items) {
    const line = lines[lines.length - 1];
    if (!line || Math.abs(item.y - line.y) > visualLineTolerance) {
      lines.push({ y: item.y, text: [item.text.trim()] });
    } else {
      line.text.push(item.text.trim());
    }
  }

  return lines.map((line) => line.text.join(' ')).join('\n');
}
