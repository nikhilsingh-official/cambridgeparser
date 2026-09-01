
import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeTrustedAnswerKey } from '../supabase/functions/fetch-pdf/trustedAnswerKey.ts';

test('normalizes a complete answer table for the trusted RPC', () => {
  assert.deepEqual(normalizeTrustedAnswerKey([
    { question: 1, answer: 'A', marks: '1', page: 1, y: 100 },
    { question: 2, answer: 'D', marks: '2', page: 1, y: 90 },
  ]), [
    { question_number: 1, correct_option: 0, option_count: 4, marks: 1 },
    { question_number: 2, correct_option: 3, option_count: 4, marks: 2 },
  ]);
});

test('rejects gaps, duplicate questions and non-option answers', () => {
  assert.equal(normalizeTrustedAnswerKey([
    { question: 1, answer: 'A', marks: '1', page: 1, y: 100 },
    { question: 3, answer: 'B', marks: '1', page: 1, y: 90 },
  ]), null);
  assert.equal(normalizeTrustedAnswerKey([
    { question: 1, answer: 'A', marks: '1', page: 1, y: 100 },
    { question: 1, answer: 'B', marks: '1', page: 1, y: 90 },
  ]), null);
  assert.equal(normalizeTrustedAnswerKey([
    { question: 1, answer: 'A or B', marks: '1', page: 1, y: 100 },
  ]), null);
});
