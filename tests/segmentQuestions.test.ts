// ==========================================================================
//
// Regression tests for geometry-based question segmentation and page furniture.
// ==========================================================================

import assert from 'node:assert/strict';
import test from 'node:test';
import { segmentQuestions } from '../src/lib/pdf/segmentQuestions.ts';
import type { indexed_textbox, textbox } from '../src/lib/pdf/pdfTypes.ts';

function box(text: string, y: number): textbox {
  return {
    text,
    font: 'Body',
    rawFontName: 'Body',
    x: 72,
    y,
    x2: 180,
    y2: y + 10,
    width: 108,
    height: 10,
    fontSize: 10,
    transform: [],
  };
}

test('question prose beginning with Turn is not mistaken for page furniture', () => {
  const marker = { ...box('1', 80), index: 0 } satisfies indexed_textbox;
  const instruction = box('Turn the handle clockwise.', 100);
  const footer = box('[Turn over', 720);

  const pages = segmentQuestions(
    [[marker, instruction, footer]],
    [[marker]],
  );

  assert.deepEqual(
    pages[0]?.[0]?.segmentText.map((item) => item.text),
    ['1', 'Turn the handle clockwise.'],
  );
});
