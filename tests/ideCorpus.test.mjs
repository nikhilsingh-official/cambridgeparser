// ===========================================================================
//
// Deployment-contract tests for the IDE corpus. These catch the two silent
// failures that previously shipped: ignored screenshot assets and a trusted
// grading corpus stripped of every answer and rubric point.
// ===========================================================================
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJson = async relativePath => JSON.parse(
  await readFile(path.join(root, relativePath), 'utf8'),
);

test('every IDE screenshot referenced by a layout is a real PNG asset', async () => {
  const payload = await readJson('public/resources/question_layouts.json');
  const references = Object.values(payload.layouts || {}).flatMap(layout => (
    ['image', 'context_image']
      .map(key => layout[key]?.src)
      .filter(Boolean)
  ));

  assert.equal(new Set(references).size, 325);
  for (const reference of references) {
    const bytes = await readFile(path.join(root, 'public/resources', reference));
    assert.equal(bytes.subarray(1, 4).toString('ascii'), 'PNG', reference);
  }
});

test('the Edge Function corpus retains trusted answers and structured rubrics', async () => {
  const payload = await readJson('supabase/functions/grade/pseudocode_question_records.json');
  assert.equal(payload.records.length, 176);
  assert.equal(
    payload.records.filter(record => record.mark_scheme?.answer_text?.trim()).length,
    176,
    'every grading record needs examiner-answer text',
  );
  assert.equal(
    payload.records.filter(record => record.mark_scheme?.marking_points?.length).length,
    176,
  );
  assert.ok(payload.records.every(record => Number.isInteger(record.mark_scheme?.max_marks)));
});

test('the browser corpus does not expose mark-scheme answers before submission', async () => {
  const payload = await readJson('public/resources/pseudocode_question_records.json');
  assert.equal(payload.records.length, 176);
  assert.ok(payload.records.every(record => !record.mark_scheme?.answer_text));
  assert.ok(payload.records.every(record => !record.mark_scheme?.marking_points));
});
