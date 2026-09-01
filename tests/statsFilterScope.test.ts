
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  aggregateDailyActivity,
  aggregateHourOfDay,
  aggregateSubjectStats,
  calibrationFromFlags,
  summariseAnswerChangeRows,
} from '../src/lib/stats/filterScope.ts';

const attempt = (overrides: Record<string, unknown>) => ({
  id: 'attempt',
  user_id: 'user-1',
  subject_code: '0478',
  subject_name: 'Computer Science',
  started_at: '2026-01-01T02:30:00.000Z',
  finished_at: '2026-01-01T03:30:00.000Z',
  client_timezone: 'Asia/Kolkata',
  local_date: '2026-01-01',
  duration_ms: 3_600_000,
  questions_recorded: 40,
  questions_correct: 25,
  marks_awarded: 25,
  marks_total: 40,
  ...overrides,
});

test('subject aggregation remains marks-weighted within the filtered attempt set', () => {
  const rows = aggregateSubjectStats([
    attempt({ id: 'a', marks_awarded: 8, marks_total: 10 }),
    attempt({ id: 'b', marks_awarded: 20, marks_total: 40, duration_ms: 1_800_000 }),
  ] as never[]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0]?.attempts, 2);
  assert.equal(rows[0]?.marks_awarded, 28);
  assert.equal(rows[0]?.marks_total, 50);
  assert.equal(rows[0]?.accuracy, 28 / 50);
  assert.equal(rows[0]?.total_time_ms, 5_400_000);
});

test('engagement aggregates are rebuilt from the same filtered attempts', () => {
  const attempts = [
    attempt({ id: 'a' }),
    attempt({
      id: 'b', started_at: '2026-01-01T03:45:00.000Z',
      duration_ms: 1_800_000, questions_recorded: 20, questions_correct: 10,
    }),
  ] as never[];

  assert.deepEqual(aggregateDailyActivity(attempts), [{
    user_id: 'user-1', local_date: '2026-01-01', papers: 2,
    total_time_ms: 5_400_000, questions: 60, correct: 35,
  }]);
  assert.deepEqual(aggregateHourOfDay(attempts), [
    { user_id: 'user-1', local_hour: 8, papers: 1, total_time_ms: 3_600_000 },
    { user_id: 'user-1', local_hour: 8 + 1, papers: 1, total_time_ms: 1_800_000 },
  ]);
});

test('calibration is computed from the already scoped question flags', () => {
  const rows = calibrationFromFlags([
    { confidence: 0.1, is_correct: true },
    { confidence: 0.18, is_correct: false },
    { confidence: 0.9, is_correct: true },
    { confidence: null, is_correct: false },
  ] as never[], 5);

  assert.equal(rows.length, 2);
  assert.equal(rows[0]?.questions, 2);
  assert.ok(Math.abs((rows[0]?.meanConfidence ?? 0) - 0.14) < 1e-12);
  assert.equal(rows[0]?.observedAccuracy, 0.5);
  assert.ok(Math.abs((rows[0]?.gap ?? 0) - 0.36) < 1e-12);
  assert.equal(rows[1]?.questions, 1);
  assert.equal(rows[1]?.meanConfidence, 0.9);
  assert.equal(rows[1]?.observedAccuracy, 1);
});

test('answer-change summary is derived only from rows returned for the scope', () => {
  assert.deepEqual(summariseAnswerChangeRows([
    { verdict: 'wrong_to_right' },
    { verdict: 'wrong_to_right' },
    { verdict: 'right_to_wrong' },
    { verdict: 'wrong_to_wrong' },
  ]), {
    changes: 4,
    wrongToRight: 2,
    rightToWrong: 1,
    wrongToWrong: 1,
    netMarks: 1,
  });
  assert.equal(summariseAnswerChangeRows([]), null);
});
