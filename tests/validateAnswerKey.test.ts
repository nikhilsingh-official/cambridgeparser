// ============================================================================
// ============================================================================

import test from 'node:test';
import assert from 'node:assert/strict';
import { validateAnswerKey } from '../src/lib/pdf/validateAnswerKey.ts';

const row = (question: number, answer = 'A') => ({
  question,
  answer,
  marks: '1',
  page: 1,
  y: 100 - question,
});

test('validateAnswerKey accepts and normalizes a complete contiguous key', () => {
  assert.deepEqual(validateAnswerKey([row(1, ' a '), row(2, 'D')]), [
    row(1, 'A'),
    row(2, 'D'),
  ]);
});

test('validateAnswerKey rejects missing, duplicate, and out-of-order questions', () => {
  assert.equal(validateAnswerKey([row(1), row(3)]), null);
  assert.equal(validateAnswerKey([row(1), row(1)]), null);
  assert.equal(validateAnswerKey([row(2), row(1)]), null);
});

test('validateAnswerKey rejects malformed options, marks, and coordinates', () => {
  assert.equal(validateAnswerKey([row(1, 'E')]), null);
  assert.equal(validateAnswerKey([{ ...row(1), marks: '0' }]), null);
  assert.equal(validateAnswerKey([{ ...row(1), page: 0 }]), null);
  assert.equal(validateAnswerKey([{ ...row(1), y: Number.NaN }]), null);
});
