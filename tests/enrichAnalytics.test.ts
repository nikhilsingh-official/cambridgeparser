// ============================================================================
//
// Public-behaviour tests for the solver's per-question analytics enrichment.
// ============================================================================

import assert from 'node:assert/strict';
import test from 'node:test';
import { build } from 'esbuild';
import type { QuestionsAnalytics } from '../src/lib/processing/processingTypes.ts';
import type { ButtonEvent, EventLogs } from '../src/lib/utils/utilsTypes.ts';

// application modules use Vite-style extensionless imports. Bundle the
// public module in memory so this Node test exercises the same module graph
// without rewriting production imports merely for the test runner.
const bundled = await build({
  entryPoints: ['src/lib/processing/enrichAnalytics.ts'],
  bundle: true,
  format: 'esm',
  platform: 'node',
  write: false,
});
const moduleUrl = `data:text/javascript;base64,${Buffer.from(bundled.outputFiles[0]!.contents).toString('base64')}`;
const { enrichAnalytics } = await import(moduleUrl) as typeof import('../src/lib/processing/enrichAnalytics.ts');

const baseQuestions = (): QuestionsAnalytics => [{
  questionNumber: 1,
  qCorrect: true,
  selectedOption: 'A',
  eliminatedOptions: [],
  time: 30,
}];

const buttonEvent = (
  elementType: ButtonEvent['elementType'],
  actionType: ButtonEvent['actionType'] = 'Selection',
  seq = 0,
): ButtonEvent => ({
  elementType,
  actionType,
  question: 1,
  dateTimestamp: '2026-09-04T00:00:00.000Z',
  performanceTimestamp: 1_000,
  timezone: 'UTC',
  seq,
  elapsedMs: 1_000,
});

function score(events: EventLogs) {
  return enrichAnalytics(baseQuestions(), events)[0]!;
}

test('explicit difficulty and interest actions increase their named scores', () => {
  const untouched = score([]);
  const starred = score([buttonEvent('Star')]);
  const saved = score([buttonEvent('Save')]);
  const flagged = score([buttonEvent('Flag')]);

  assert.ok(
    starred.difficultyScore! > untouched.difficultyScore!,
    'starring a question must increase its inferred difficulty',
  );
  assert.ok(
    saved.interestScore! > untouched.interestScore!,
    'saving a question must increase its inferred interest',
  );
  assert.ok(
    flagged.interestScore! > untouched.interestScore!,
    'flagging a question for review must increase its inferred interest',
  );
});

test('toggle analytics use final state rather than historical selection count', () => {
  const untouched = score([]);
  const toggledOff = score([
    buttonEvent('Star', 'Selection', 0),
    buttonEvent('Star', 'Deselection', 1),
  ]);
  const selectedAfterCycle = score([
    buttonEvent('Save', 'Selection', 0),
    buttonEvent('Save', 'Deselection', 1),
    buttonEvent('Save', 'Selection', 2),
  ]);
  const selectedOnce = score([buttonEvent('Save')]);

  assert.equal(toggledOff.markedAsDifficult, 0);
  assert.equal(toggledOff.difficultyScore, untouched.difficultyScore);
  assert.equal(selectedAfterCycle.markedForSave, 1);
  assert.equal(selectedAfterCycle.interestScore, selectedOnce.interestScore);
});
