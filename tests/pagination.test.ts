
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import { fetchCountedPages } from '../src/lib/supabase/queries/pagination.ts';

test('counted pagination keeps reading when the server returns fewer rows than requested', async () => {
  const source = Array.from({ length: 2_305 }, (_, index) => index);
  const ranges: Array<[number, number]> = [];

  const rows = await fetchCountedPages('practice', 10_000, async (from, to) => {
    ranges.push([from, to]);
    // Simulate a hosted PostgREST max_rows cap lower than the requested range.
    const data = source.slice(from, Math.min(to + 1, from + 1_000));
    return { data, error: null, count: source.length };
  });

  assert.equal(rows.length, source.length);
  assert.deepEqual(ranges, [[0, 9_999], [1_000, 10_999], [2_000, 11_999]]);
  assert.deepEqual(rows, source);
});

test('counted pagination stops safely when an empty page is returned', async () => {
  let calls = 0;
  const rows = await fetchCountedPages<number>('practice', 10_000, async () => {
    calls += 1;
    return { data: [], error: null, count: 20 };
  });

  assert.deepEqual(rows, []);
  assert.equal(calls, 1);
});

test('local PostgREST allows a 10,000-row response', async () => {
  const config = await readFile(new URL('../supabase/config.toml', import.meta.url), 'utf8');
  assert.match(config, /^max_rows = 10000$/m);
});
