// ==========================================================================
//
// Release-boundary tests for papers exposed by the browser catalogue.
// ==========================================================================

import assert from 'node:assert/strict';
import test from 'node:test';
import { createServer } from 'vite';

test('paper catalogue does not expose 2016 or earlier cards', async () => {
  const vite = await createServer({
    appType: 'custom',
    logLevel: 'error',
    server: { middlewareMode: true, hmr: { port: 24680 } },
  });

  try {
    const catalogue = await vite.ssrLoadModule('/src/constants/paperCatalogue.ts');
    assert.ok(catalogue.CATALOGUE_YEARS.every((year: number) => year >= 2017));
    assert.deepEqual(catalogue.buildPaperEntries({
      subjectCodes: [],
      examYears: [2016],
      series: [],
      variants: [],
    }), []);
  } finally {
    await vite.close();
  }
});

test('paper catalogue applies verified sitting and variant exclusions', async () => {
  const vite = await createServer({
    appType: 'custom',
    logLevel: 'error',
    server: { middlewareMode: true, hmr: { port: 24681 } },
  });

  try {
    const catalogue = await vite.ssrLoadModule('/src/constants/paperCatalogue.ts');
    const entries = catalogue.buildPaperEntries({
      subjectCodes: [],
      examYears: [],
      series: [],
      variants: [],
    });
    const ids = new Set(entries.map((entry: { id: string }) => entry.id));

    assert.ok(entries.every((entry: { id: string }) => !/_s20_/.test(entry.id)));
    assert.ok(entries.every((entry: { id: string }) => !/_w26_/.test(entry.id)));
    assert.ok(entries.every((entry: { id: string }) => !/^0654_[msw]17_/.test(entry.id)));
    assert.ok(entries.every((entry: { id: string }) => !/^0654_m(?:18|19|20)_/.test(entry.id)));
    assert.ok(!ids.has('2281_w23_13'));
    assert.ok(!ids.has('9700_m20_12'));
    assert.ok(!ids.has('9708_s24_12'));

    const economics = entries.filter((entry: { code: string }) => entry.code === '2281');
    assert.ok(economics.every((entry: { series: string; variant: number }) =>
      entry.series === 's' ? [1, 2].includes(entry.variant) : [2, 3].includes(entry.variant)));
  } finally {
    await vite.close();
  }
});
