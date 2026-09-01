
import assert from 'node:assert/strict';
import test from 'node:test';

import { loadStatsSections } from '../src/lib/stats/loadStatsSections.ts';

test('stats section loading preserves successful sections when another query fails', async () => {
  const results = await loadStatsSections({
    progress: async () => ({ attempts: [1] }),
    topics: async () => { throw new Error('topic practice failed'); },
    focus: async () => ({ flags: [2] }),
  });

  assert.deepEqual(results.progress.data, { attempts: [1] });
  assert.equal(results.progress.error, null);
  assert.equal(results.topics.data, null);
  assert.equal(results.topics.error, 'topic practice failed');
  assert.deepEqual(results.focus.data, { flags: [2] });
});
