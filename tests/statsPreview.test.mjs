// ===========================================================================
//
// Regression contract for the dashboard's rotating statistics preview. Every
// card owns a trend graph; inactive cards keep a compact graph and only the
// active card receives the expanded graph geometry.
// ===========================================================================
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../src/components_dashboard/StatsPrev.vue', import.meta.url),
  'utf8',
);

test('all rotating stats cards render a trend graph', () => {
  assert.match(source, /v-for="\(tile, i\) in cards"[\s\S]*?<MiniTrend/);
  assert.doesNotMatch(
    source,
    /\.inactive\s+:deep\(\.mini-trend\)\s*\{[^}]*opacity:\s*0/,
  );
});

test('inactive trends stay compact and only the active trend expands', () => {
  const inactive = source.match(/\.inactive\s+:deep\(\.mini-trend\)\s*\{([^}]*)\}/)?.[1] ?? '';
  const active = source.match(/\.active\s+:deep\(\.mini-trend\)\s*\{([^}]*)\}/)?.[1] ?? '';

  assert.match(inactive, /inset:/);
  assert.match(active, /inset:/);
  assert.notEqual(inactive.match(/inset:\s*([^;]+)/)?.[1], active.match(/inset:\s*([^;]+)/)?.[1]);
});
