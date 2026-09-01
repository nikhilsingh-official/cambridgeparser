// ==========================================================================
// ==========================================================================

import test from 'node:test';
import assert from 'node:assert/strict';
import { localIsoDate } from '../src/lib/date/localIsoDate.ts';

test('localIsoDate uses the requested calendar timezone, not UTC', () => {
  const instant = new Date('2026-08-27T20:00:00.000Z');

  assert.equal(localIsoDate(instant, 'UTC'), '2026-08-27');
  assert.equal(localIsoDate(instant, 'Asia/Kolkata'), '2026-08-28');
  assert.equal(localIsoDate(instant, 'America/Los_Angeles'), '2026-08-27');
});
