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

  // all 381 canonical questions now have a rendered question image, with
  // context renders for every sub-question that needs its parent prompt.
  assert.equal(new Set(references).size, 698);
  for (const reference of references) {
    const bytes = await readFile(path.join(root, 'public/resources', reference));
    assert.equal(bytes.subarray(1, 4).toString('ascii'), 'PNG', reference);
  }
});

test('the Edge Function corpus retains trusted answers and structured rubrics', async () => {
  const payload = await readJson('supabase/functions/grade/pseudocode_question_records.json');
  // 176 AS/A Level records plus 205 unique IGCSE records.
  assert.equal(payload.records.length, 381);
  assert.equal(
    payload.records.filter(record => record.mark_scheme?.answer_text?.trim()).length,
    381,
    'every grading record needs examiner-answer text',
  );
  assert.equal(
    payload.records.filter(record => record.mark_scheme?.marking_points?.length).length,
    381,
  );
  assert.ok(payload.records.every(record => Number.isInteger(record.mark_scheme?.max_marks)));
  // generated reporting metadata must agree with the discarded rows it
  // summarizes, even though those rows are not used by the runtime grader.
  const discardReasons = (payload.discarded || []).reduce((counts, record) => {
    counts[record.reason] = (counts[record.reason] || 0) + 1;
    return counts;
  }, {});
  assert.deepEqual(payload.summary?.discard_reasons, discardReasons);
  // canonical records originate in 65 IGCSE papers; duplicate provenance
  // retains the four variants whose questions were wholly duplicated, proving
  // that all 69 valid 0478 papers were processed rather than silently skipped.
  const igcseRecords = payload.records.filter(record => record.paper_code?.startsWith('0478_'));
  const igcseSourcePapers = new Set(igcseRecords.map(record => record.paper_code));
  for (const record of igcseRecords) {
    for (const duplicate of record.provenance?.duplicate_sources || []) {
      if (duplicate.paper_code?.startsWith('0478_')) igcseSourcePapers.add(duplicate.paper_code);
    }
  }
  assert.equal(igcseRecords.length, 205);
  assert.equal(igcseSourcePapers.size, 69);
});

test('the browser corpus does not expose mark-scheme answers before submission', async () => {
  const payload = await readJson('public/resources/pseudocode_question_records.json');
  assert.equal(payload.records.length, 381);
  assert.ok(payload.records.every(record => !record.mark_scheme?.answer_text));
  assert.ok(payload.records.every(record => !record.mark_scheme?.marking_points));
  // pin the syllabus-level outcome so a later corpus rebuild cannot
  // silently drop the newly extracted IGCSE records.
  assert.equal(
    payload.records.filter(record => record.paper_code?.startsWith('0478_')).length,
    205,
  );
  // IGCSE tags must cite 0478 Topics 7–8, never 9618 sections 9–12.
  const igcseTags = payload.records
    .filter(record => record.paper_code?.startsWith('0478_'))
    .flatMap(record => record.syllabus_tags || []);
  assert.ok(igcseTags.length > 0);
  assert.ok(igcseTags.every(tag => ['7', '8'].includes(tag.section)));
  assert.ok(igcseTags.every(tag => tag.syllabus_ref.startsWith(`${tag.section}.`)));
  assert.ok(igcseTags.every(tag => (
    tag.section_label === 'Algorithm design and problem-solving'
      || tag.section_label === 'Programming'
  )));
});
