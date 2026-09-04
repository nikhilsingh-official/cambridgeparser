// ============================================================================
//
// Public solver navigation and segmented-question text contract tests.
// ============================================================================

import assert from 'node:assert/strict';
import test from 'node:test';
import { activateQuestionFocus } from '../src/lib/focusAreas/activateQuestionFocus.ts';
import { segmentedQuestionText } from '../src/lib/pdf/segmentedQuestionText.ts';
import type { DocumentFocusAreas } from '../src/lib/focusAreas/focusAreasTypes.ts';
import type { SegmentedQuestions, textbox } from '../src/lib/pdf/pdfTypes.ts';

test('question navigation activates only the requested focus area', () => {
  const areas: DocumentFocusAreas = [[
    { questionNumber: 1, y: 10, y2: 50, active: true, time: 4 },
    { questionNumber: 2, y: 60, y2: 100, active: false, time: 0 },
  ]];

  const target = activateQuestionFocus(areas, 2);

  assert.equal(target?.pageIndex, 0);
  assert.equal(target?.focusArea.questionNumber, 2);
  assert.equal(areas[0]![0]!.active, false);
  assert.equal(areas[0]![1]!.active, true);
  assert.equal(activateQuestionFocus(areas, 99), null);
});

function box(text: string, x: number, y: number): textbox {
  return {
    text,
    x,
    y,
    x2: x + 20,
    y2: y + 10,
    width: 20,
    height: 10,
    fontSize: 10,
    font: 'Body',
    rawFontName: 'Body',
    transform: [],
  };
}

test('copy text returns the requested segmented question in visual reading order', () => {
  const questions: SegmentedQuestions = [[
    {
      segmentText: [box('1', 10, 10), box('First question', 30, 10)],
      averageY: 20,
      contentY: 10,
      contentY2: 20,
    },
    {
      // stream order is deliberately scrambled; visible order is y then x.
      segmentText: [
        box('option', 40, 40),
        box('2', 10, 20),
        box('A', 20, 40),
        box('Second question?', 30, 20),
      ],
      averageY: 35,
      contentY: 20,
      contentY2: 50,
    },
  ]];

  assert.equal(segmentedQuestionText(questions, 2), '2 Second question?\nA option');
  assert.equal(segmentedQuestionText(questions, 99), null);
});
