
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
    marking_points: [{ id: 'mp1', text: 'one', marks: 3 }],
  },
};

test('Edge grader preserves the score cap and grading-result validation seam', () => {
  assert.equal(resolveMaxMarks(record), 3);
  const result = applyMaxMarksCap({
    total_awarded: 5,
    max_marks: 5,
    points: [{
      marking_point_id: 'mp1', awarded: true, marks_awarded: 3,
      confidence: 'high', evidence: 'OUTPUT x', concerns: [],
    }],
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

test('Edge grader rejects negative scores, numeric strings and malformed concerns', () => {
  const valid = {
    total_awarded: 1,
    max_marks: 3,
    points: [{
      marking_point_id: 'mp1', awarded: true, marks_awarded: 1,
      confidence: 'high', evidence: 'OUTPUT x', concerns: [],
    }],
    overall_explanation: 'Supported.',
  };

  assert.match(validateGradingPayload({ ...valid, total_awarded: -1 }) ?? '', /non-negative/);
  assert.match(validateGradingPayload({ ...valid, max_marks: '3' }) ?? '', /integer/);
  assert.match(validateGradingPayload({
    ...valid,
    points: [{ ...valid.points[0], marks_awarded: -1 }],
  }) ?? '', /non-negative/);
  assert.match(validateGradingPayload({
    ...valid,
    points: [{ ...valid.points[0], concerns: ['valid', 7] }],
  }) ?? '', /concerns/);
});

test('Edge grader validates model scores against the trusted rubric', () => {
  const base = {
    total_awarded: 3,
    max_marks: 3,
    points: [{
      marking_point_id: 'mp1', awarded: true, marks_awarded: 3,
      confidence: 'high', evidence: 'OUTPUT x', concerns: [],
    }],
    overall_explanation: 'Supported.',
  };

  assert.equal(validateGradingPayload(base, record), null);
  assert.match(validateGradingPayload({
    ...base,
    points: [{ ...base.points[0], marking_point_id: 'invented' }],
  }, record) ?? '', /unknown marking point/);
  assert.match(validateGradingPayload({
    ...base,
    total_awarded: 2,
  }, record) ?? '', /sum/);
  assert.match(validateGradingPayload({
    ...base,
    points: [{ ...base.points[0], awarded: false }],
  }, record) ?? '', /unawarded/);
});

test('only provider-side Google failures trigger fallback', () => {
  assert.equal(classifyGoogleFailure(429, ''), 'rate_limit');
  assert.equal(classifyGoogleFailure(403, 'RESOURCE_EXHAUSTED'), 'rate_limit');
  assert.equal(classifyGoogleFailure(404, 'NOT_FOUND'), 'model_unavailable');
  assert.equal(classifyGoogleFailure(503, 'temporarily unavailable'), 'provider_unavailable');
  assert.equal(classifyGoogleFailure(504, 'gateway timeout'), 'provider_unavailable');
  assert.equal(classifyGoogleFailure(408, 'request timeout'), 'provider_unavailable');
  assert.equal(classifyGoogleFailure(400, 'bad schema'), null);
});

test('Google success is normalized into grading-result/v1 and capped', async () => {
  const providerPayload = {
    total_awarded: 4,
    max_marks: 4,
    points: [{
      marking_point_id: 'mp1', awarded: true, marks_awarded: 3,
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

test('Google 503 retries once and then falls back to OpenRouter', async () => {
  let googleCalls = 0;
  let openRouterCalls = 0;
  const providerPayload = {
    total_awarded: 3,
    max_marks: 3,
    points: [{
      marking_point_id: 'mp1', awarded: true, marks_awarded: 3,
      confidence: 'high', evidence: 'OUTPUT x', concerns: [],
    }],
    overall_explanation: 'Supported.',
  };
  const fakeFetch = async (input: string | URL | Request) => {
    const url = String(input);
    if (url.includes('generativelanguage')) {
      googleCalls += 1;
      return new Response('temporarily unavailable', { status: 503 });
    }
    openRouterCalls += 1;
    return new Response(JSON.stringify({
      choices: [{ message: { content: JSON.stringify(providerPayload) } }],
    }));
  };

  const result = await gradeTrustedRecord(
    { id: 1, ...record },
    { source_text: 'OUTPUT x', parse: { ok: true, ast: {}, diagnostics: [] } },
    {
      googleKey: 'google-test', googleModels: ['test-model', 'unused-model'],
      openRouterKey: 'openrouter-test',
    },
    fakeFetch as typeof fetch,
  );

  assert.equal(googleCalls, 2);
  assert.equal(openRouterCalls, 1);
  assert.equal(result.ok, true);
  assert.equal(result.provider, 'openrouter');
  assert.equal(result.fallback_from.reason, 'provider_unavailable');
});

test('Google outage without OpenRouter reports the provider failure, not missing configuration', async () => {
  const fakeFetch = async () => new Response('temporarily unavailable', { status: 503 });
  const result = await gradeTrustedRecord(
    { id: 1, ...record },
    { source_text: 'OUTPUT x', parse: { ok: true, ast: {}, diagnostics: [] } },
    { googleKey: 'google-test', googleModels: ['test-model'] },
    fakeFetch as typeof fetch,
  );

  assert.equal(result.ok, false);
  assert.equal(result.fallback_reason, 'provider_unavailable');
  assert.match(result.error, /HTTP 503/);
  assert.doesNotMatch(result.error, /not configured/);
});
