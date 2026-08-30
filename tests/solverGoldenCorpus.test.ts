// ==========================================================================
//
// Contract tests for the solver's reviewed PDF corpus manifest.
// ==========================================================================

import assert from 'node:assert/strict';
import test from 'node:test';
import {
  EXPECTED_SOLVER_PAPER_FAMILIES,
  loadSolverGoldenCorpus,
  validateSolverGoldenCorpus,
} from '../scripts/solver-corpus/manifest.ts';
import {
  solverCorpusSourceUrl,
  verifySolverCorpusSource,
} from '../scripts/solver-corpus/fetch.ts';
import { classifySolverCorpusChecks } from '../scripts/solver-corpus/validate.ts';

test('golden corpus covers every solver paper family exactly once', async () => {
  const corpus = await loadSolverGoldenCorpus();
  const actualFamilies = corpus.papers
    .map((paper) => `${paper.subjectCode}/${paper.paperNumber}`)
    .sort();

  assert.deepEqual(actualFamilies, [...EXPECTED_SOLVER_PAPER_FAMILIES].sort());
  assert.equal(new Set(corpus.papers.map((paper) => paper.paperId)).size, corpus.papers.length);

  const years = corpus.papers.map((paper) => paper.year);
  assert.equal(Math.min(...years), 2017, 'the earliest supported PDF generation must be represented');
  assert.ok(Math.max(...years) >= 2025, 'the current PDF generation must be represented');
  assert.deepEqual(
    [...new Set(corpus.papers.map((paper) => paper.series))].sort(),
    ['m', 's', 'w'],
  );
});

test('golden corpus contains complete, checksum-pinned independent expectations', async () => {
  const corpus = await loadSolverGoldenCorpus();
  const errors = validateSolverGoldenCorpus(corpus);

  assert.deepEqual(errors, []);
  for (const paper of corpus.papers) {
    assert.equal(paper.expected.answerKey.length, paper.expected.questionCount);
    assert.equal(
      paper.expected.pageQuestionCounts.reduce((sum, count) => sum + count, 0),
      paper.expected.questionCount,
    );
    assert.equal(paper.expected.pageQuestionCounts.length, paper.sources.questionPaper.pages);
  }
});

test('golden corpus includes reviewed geometry and option-association probes', async () => {
  const corpus = await loadSolverGoldenCorpus();
  const geometryPaperIds = new Set(
    corpus.papers.filter((paper) => paper.expected.geometryProbes.length > 0)
      .map((paper) => paper.paperId),
  );
  const associationPaperIds = new Set(
    corpus.papers.filter((paper) => paper.expected.optionTextProbes.length > 0)
      .map((paper) => paper.paperId),
  );

  assert.ok(geometryPaperIds.size >= 6, 'at least six layout families need coordinate truth');
  assert.ok(associationPaperIds.has('2281_w25_13'));
  assert.ok(associationPaperIds.has('9708_s25_13'));
  assert.ok(associationPaperIds.has('9701_m25_12'));
});

test('corpus fetch boundary pins both source identity and bytes', () => {
  const bytes = new TextEncoder().encode('%PDF-golden fixture');
  const expected = {
    file: 'paper.pdf',
    bytes: 19,
    pages: 1,
    sha256: '703b6287aa8a5f3bd5580482ecfd1c762ddbcedceda262a5b9918bb5ffc4b20e',
  };

  assert.equal(
    solverCorpusSourceUrl('https://example.test/base/', expected),
    'https://example.test/base/paper.pdf',
  );
  assert.equal(verifySolverCorpusSource(bytes, expected), null);
  assert.match(
    verifySolverCorpusSource(new TextEncoder().encode('changed fixture'), expected) ?? '',
    /byte count|SHA-256/,
  );
});

test('corpus audit distinguishes known failures, regressions and fixed expectations', () => {
  const classified = classifySolverCorpusChecks(
    [
      { check: 'qp.question-count', passed: true, detail: '40 questions' },
      { check: 'qp.option-count:8', passed: false, detail: 'found 1, expected 4' },
      { check: 'ms.answer-key', passed: false, detail: 'found 0 answers' },
    ],
    [{ check: 'qp.option-count:8', reason: 'known graph question' }],
  );

  assert.deepEqual(classified.knownFailures.map((result) => result.check), ['qp.option-count:8']);
  assert.deepEqual(classified.unexpectedFailures.map((result) => result.check), ['ms.answer-key']);
  assert.deepEqual(classified.unexpectedPasses, []);

  const fixed = classifySolverCorpusChecks(
    [{ check: 'qp.option-count:8', passed: true, detail: '4 options' }],
    [{ check: 'qp.option-count:8', reason: 'known graph question' }],
  );
  assert.deepEqual(fixed.unexpectedPasses.map((result) => result.check), ['qp.option-count:8']);
});
