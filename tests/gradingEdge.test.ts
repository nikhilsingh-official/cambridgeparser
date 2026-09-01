
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  applyMaxMarksCap,
  classifyGoogleFailure,
  extractJsonObject,
  gradeTrustedRecord,
  resolveMaxMarks,
  validateGradingPayload,
} from '../supabase/functions/grade/grading.ts';

const record = {
  mark_scheme: {
    max_marks: 3,
    marking_points: [{ id: 'mp1', text: 'one', marks: 1 }],
  },
};

test('Edge grader preserves the score cap and grading-result validation seam', () => {
  assert.equal(resolveMaxMarks(record), 3);
  const result = applyMaxMarksCap({
    total_awarded: 5,
    max_marks: 5,
    points: [],
    overall_explanation: 'Awarded.',
  }, 3);
  assert.equal(result.total_awarded, 3);
  assert.deepEqual(result.cap_applied, { reported_total: 5, max_marks: 3 });
  assert.equal(validateGradingPayload(result), null);
});

test('Edge grader extracts fenced JSON and rejects malformed marking points', () => {
  assert.deepEqual(extractJsonObject('```json\n{"ok":true}\n```'), { ok: true });
  assert.match(validateGradingPayload({
    total_awarded: 1,
    max_marks: 1,
    points: [{ marking_point_id: 'mp1', awarded: 'yes' }],
    overall_explanation: 'x',
  }) ?? '', /awarded/);
});

test('only provider-side Google failures trigger fallback', () => {
  assert.equal(classifyGoogleFailure(429, ''), 'rate_limit');
  assert.equal(classifyGoogleFailure(403, 'RESOURCE_EXHAUSTED'), 'rate_limit');
  assert.equal(classifyGoogleFailure(404, 'NOT_FOUND'), 'model_unavailable');
  assert.equal(classifyGoogleFailure(400, 'bad schema'), null);
});

test('Google success is normalized into grading-result/v1 and capped', async () => {
  const providerPayload = {
    total_awarded: 4,
    max_marks: 4,
    points: [{
      marking_point_id: 'mp1', awarded: true, marks_awarded: 4,
      confidence: 'high', evidence: 'OUTPUT x', concerns: [],
    }],
    overall_explanation: 'Supported.',
  };
  const fakeFetch = async () => new Response(JSON.stringify({
    candidates: [{ content: { parts: [{ text: JSON.stringify(providerPayload) }] } }],
  })) as Promise<Response>;
  const result = await gradeTrustedRecord(
    { id: 1, ...record },
    { source_text: 'OUTPUT x', parse: { ok: true, ast: {}, diagnostics: [] } },
    { googleKey: 'test', googleModels: ['test-model'] },
    fakeFetch as typeof fetch,
  );
  assert.equal(result.schema_version, 'grading-result/v1');
  assert.equal(result.ok, true);
  assert.equal(result.provider, 'google-ai-studio');
  assert.equal(result.result.total_awarded, 3);
});
