// ============================================================================
// ============================================================================

import type { DocumentFocusAreas, FocusArea } from './focusAreasTypes.ts';

export interface QuestionFocusTarget {
  pageIndex: number;
  focusArea: FocusArea;
}

/** Make one parsed question the sole active focus area. */
export function activateQuestionFocus(
  documentFocusAreas: DocumentFocusAreas,
  questionNumber: number,
): QuestionFocusTarget | null {
  let target: QuestionFocusTarget | null = null;

  for (let pageIndex = 0; pageIndex < documentFocusAreas.length; pageIndex++) {
    for (const focusArea of documentFocusAreas[pageIndex] ?? []) {
      if (focusArea.questionNumber === questionNumber) {
        target = { pageIndex, focusArea };
      }
    }
  }

  if (!target) return null;
  for (const focusArea of documentFocusAreas.flat()) {
    focusArea.active = focusArea === target.focusArea;
  }
  return target;
}
