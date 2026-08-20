// that pinned the Paper Solver at 100% CPU. Run: npm run test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { stripInlineBackground } from '../src/lib/pdf/stripInlineBackground.ts';

test('removes background declarations', () => {
  assert.equal(stripInlineBackground('background: red; left: 4px'), 'left: 4px');
  assert.equal(stripInlineBackground('background-color: #fff; top: 0'), 'top: 0');
  assert.equal(stripInlineBackground('BACKGROUND-IMAGE: url(x); z-index: 2'), 'z-index: 2');
});

test('returns null when nothing survives, so the attribute is removed', () => {
  assert.equal(stripInlineBackground('background: red'), null);
  assert.equal(stripInlineBackground(''), null);
  assert.equal(stripInlineBackground(';;'), null);
});

test('does not strip properties that merely start with the same letters', () => {
  assert.equal(stripInlineBackground('background-blend-mode: darken; left: 1px'),
    'background-blend-mode: darken; left: 1px');
});

// THE REGRESSION. This is the property whose absence caused the bug: the
// observer writes the result back into the attribute it is observing, so a
// non-idempotent transform re-triggers itself forever.
test('is idempotent - f(f(x)) === f(x) for every input', () => {
  const inputs = [
    'left: 4px; top: 8px',
    'left:4px;top:8px',
    'background: red; left: 4px',
    'transform: scale(1.2); background-color: rgb(0,0,0); font-size: 10px',
    '  padding : 2px ;  ',
    'left: 4px; top: 8px;',
  ];
  for (const input of inputs) {
    const once = stripInlineBackground(input);
    if (once === null) continue;
    const twice = stripInlineBackground(once);
    assert.equal(twice, once, `not idempotent for ${JSON.stringify(input)}`);
  }
});

// The caller's guard: after one pass the output must equal its own input, so
// the `next !== current` check in MCQNav stops writing and the loop ends.
test('reaches a fixed point after a single pass', () => {
  let value: string | null = 'left:4px;background:red;top:8px';
  const seen: string[] = [];
  for (let i = 0; i < 5 && value !== null; i++) {
    if (seen.includes(value)) return; // converged
    seen.push(value);
    value = stripInlineBackground(value);
  }
  assert.ok(seen.length <= 2, `took ${seen.length} passes to converge: ${seen.join(' -> ')}`);
});
