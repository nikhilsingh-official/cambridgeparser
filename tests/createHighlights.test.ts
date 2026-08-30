// ==========================================================================
//
// Interaction-geometry tests for option highlights.
// ==========================================================================

import assert from 'node:assert/strict';
import test from 'node:test';
import { createServer } from 'vite';
import type { textbox } from '../src/lib/pdf/pdfTypes.ts';

function optionLabel(text: string, x: number, y: number): textbox {
  return {
    text,
    font: 'Option',
    rawFontName: 'Option',
    x,
    y,
    x2: x + 8,
    y2: y + 11,
    width: 8,
    height: 11,
    fontSize: 11,
    transform: [],
  };
}

test('label-only options receive usable click targets', async () => {
  const vite = await createServer({
    appType: 'custom',
    logLevel: 'error',
    server: { middlewareMode: true, hmr: { port: 24679 } },
  });

  try {
    const { createHighlights } = await vite.ssrLoadModule('/src/lib/highlights/createHighlights.ts');
    const labels = ['A', 'B', 'C', 'D'].map((label, index) =>
      optionLabel(label, 70, 220 + index * 40));
    const highlights = createHighlights([[[...labels.map((label) => [label])]]]);

    for (const option of highlights[0]?.[0] ?? []) {
      const target = option[0];
      assert.ok(target, 'each option needs one rendered target');
      assert.ok(target.x2 - target.x >= 20, 'label target is at least 20 PDF points wide');
      assert.ok(target.y2 - target.y >= 16, 'label target is at least 16 PDF points high');
    }
  } finally {
    await vite.close();
  }
});
