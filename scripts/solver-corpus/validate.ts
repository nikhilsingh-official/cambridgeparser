// ==========================================================================
//
// Executes and classifies checks against the solver's reviewed PDF corpus.
// ==========================================================================

import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import * as browserPdfJs from 'pdfjs-dist/legacy/build/pdf.mjs';
import { createServer } from 'vite';
import { getAnswersFromPDF, type ServerPdfJs } from '../../supabase/functions/fetch-pdf/answerKey.ts';
import { DEFAULT_SOLVER_CORPUS_CACHE, verifySolverCorpusSource } from './fetch.ts';
import {
  loadSolverGoldenCorpus,
  type KnownCorpusFailure,
  type SolverBox,
  type SolverGoldenPaper,
  type SolverOption,
} from './manifest.ts';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const EDGE_PDFJS_PATH = resolve(
  SCRIPT_DIR,
  '../../supabase/functions/fetch-pdf/node_modules/pdfjs-serverless/dist/index.mjs',
);
const GEOMETRY_TOLERANCE = 0.2;

interface ParsedTextBox {
  text: string;
  x: number;
  y: number;
  x2: number;
  y2: number;
}

interface ParsedQuestionSegment {
  segmentText: ParsedTextBox[];
}

type ParsedDocumentText = ParsedTextBox[][];
type ParsedSegments = ParsedQuestionSegment[][];
type ParsedOptions = ParsedTextBox[][][][];

interface SolverPdfPipeline {
  extractText(pdf: browserPdfJs.PDFDocumentProxy): Promise<ParsedDocumentText>;
  identifyQuestionNumbers(text: ParsedDocumentText): unknown;
  segmentQuestions(text: ParsedDocumentText, markers: unknown): ParsedSegments;
  getOptions(
    pdf: browserPdfJs.PDFDocumentProxy,
    text: ParsedDocumentText,
    segments: ParsedSegments,
  ): Promise<ParsedOptions>;
}

interface ParsedQuestion {
  page: number;
  options: ParsedTextBox[][];
}

export interface SolverCorpusCheck {
  check: string;
  passed: boolean;
  detail: string;
}

export interface ClassifiedSolverCorpusChecks {
  passed: SolverCorpusCheck[];
  knownFailures: SolverCorpusCheck[];
  unexpectedFailures: SolverCorpusCheck[];
  unexpectedPasses: SolverCorpusCheck[];
}

export interface SolverPaperAudit {
  paper: SolverGoldenPaper;
  checks: SolverCorpusCheck[];
  classified: ClassifiedSolverCorpusChecks;
}

export interface SolverCorpusAudit {
  papers: SolverPaperAudit[];
  checkCount: number;
  knownFailureCount: number;
  unexpectedFailureCount: number;
  unexpectedPassCount: number;
}

export function classifySolverCorpusChecks(
  checks: SolverCorpusCheck[],
  knownFailures: KnownCorpusFailure[],
): ClassifiedSolverCorpusChecks {
  const known = new Set(knownFailures.map((failure) => failure.check));
  const result: ClassifiedSolverCorpusChecks = {
    passed: [],
    knownFailures: [],
    unexpectedFailures: [],
    unexpectedPasses: [],
  };

  for (const check of checks) {
    if (check.passed && known.has(check.check)) {
      result.unexpectedPasses.push(check);
    } else if (check.passed) {
      result.passed.push(check);
    } else if (known.has(check.check)) {
      result.knownFailures.push(check);
    } else {
      result.unexpectedFailures.push(check);
    }
  }

  return result;
}

function exactCheck(check: string, actual: unknown, expected: unknown): SolverCorpusCheck {
  const passed = JSON.stringify(actual) === JSON.stringify(expected);
  return {
    check,
    passed,
    detail: passed
      ? `matched ${JSON.stringify(expected)}`
      : `found ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`,
  };
}

function normalizeText(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

function optionText(option: ParsedTextBox[]): string {
  return normalizeText(option.map((item) => item.text).join(' '));
}

function boxMatches(actual: ParsedTextBox, expected: SolverBox): boolean {
  const actualBox: SolverBox = [actual.x, actual.y, actual.x2, actual.y2];
  return actualBox.every(
    (coordinate, index) => Math.abs(coordinate - expected[index]!) <= GEOMETRY_TOLERANCE,
  );
}

function geometryCheck(
  question: ParsedQuestion,
  questionNumber: number,
  expectedPage: number,
  markers: Record<SolverOption, SolverBox>,
): SolverCorpusCheck {
  const items = question.options.flat();
  const missing = (['A', 'B', 'C', 'D'] as const).filter((option) =>
    !items.some((item) => item.text.trim() === option && boxMatches(item, markers[option])));
  const pageMatches = question.page === expectedPage;
  return {
    check: `qp.geometry:${questionNumber}`,
    passed: pageMatches && missing.length === 0,
    detail: pageMatches && missing.length === 0
      ? `all marker boxes matched on page ${expectedPage}`
      : `parsed page ${question.page}; missing marker boxes: ${missing.join(', ') || 'none'}`,
  };
}

async function readPinnedSource(
  cacheDir: string,
  source: SolverGoldenPaper['sources']['questionPaper'],
): Promise<Uint8Array> {
  let bytes: Uint8Array;
  try {
    bytes = new Uint8Array(await readFile(resolve(cacheDir, source.file)));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      throw new Error(
        `${source.file} is missing; run node --experimental-strip-types scripts/solver-corpus/fetch.ts`,
      );
    }
    throw error;
  }
  const verificationError = verifySolverCorpusSource(bytes, source);
  if (verificationError) throw new Error(verificationError);
  return bytes;
}

function exactArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer;
}

async function auditQuestionPaper(
  paper: SolverGoldenPaper,
  cacheDir: string,
  pipeline: SolverPdfPipeline,
): Promise<SolverCorpusCheck[]> {
  const qpBytes = await readPinnedSource(cacheDir, paper.sources.questionPaper);
  const pdf = await browserPdfJs.getDocument({ data: qpBytes }).promise;
  const checks: SolverCorpusCheck[] = [];

  try {
    checks.push(exactCheck('qp.page-count', pdf.numPages, paper.sources.questionPaper.pages));
    const text = await pipeline.extractText(pdf);
    const markers = pipeline.identifyQuestionNumbers(text);
    const segments = pipeline.segmentQuestions(text, markers);
    const questionCount = segments.reduce((sum, page) => sum + page.length, 0);
    checks.push(exactCheck('qp.question-count', questionCount, paper.expected.questionCount));

    // A wrong segmentation count invalidates the question-number mapping, so
    // downstream per-question checks would only duplicate the root failure.
    if (questionCount === paper.expected.questionCount) {
      checks.push(exactCheck(
        'qp.page-question-counts',
        segments.map((page) => page.length),
        paper.expected.pageQuestionCounts,
      ));

      const options = await pipeline.getOptions(pdf, text, segments);
      const questions: ParsedQuestion[] = [];
      for (let pageIndex = 0; pageIndex < segments.length; pageIndex++) {
        for (let segmentIndex = 0; segmentIndex < segments[pageIndex]!.length; segmentIndex++) {
          questions.push({
            page: pageIndex + 1,
            options: options[pageIndex]?.[segmentIndex] ?? [],
          });
        }
      }

      for (let index = 0; index < questions.length; index++) {
        checks.push(exactCheck(
          `qp.option-count:${index + 1}`,
          questions[index]!.options.length,
          paper.expected.optionsPerQuestion,
        ));
      }

      for (const probe of paper.expected.optionTextProbes) {
        const actual = questions[probe.question - 1]!.options.map(optionText);
        const expected = probe.options.map(normalizeText);
        checks.push(exactCheck(`qp.option-text:${probe.question}`, actual, expected));
      }

      for (const probe of paper.expected.geometryProbes) {
        checks.push(geometryCheck(
          questions[probe.question - 1]!,
          probe.question,
          probe.page,
          probe.markers,
        ));
      }
    }
  } finally {
    await pdf.destroy();
  }

  return checks;
}

export async function auditSolverGoldenCorpus(
  cacheDir = DEFAULT_SOLVER_CORPUS_CACHE,
): Promise<SolverCorpusAudit> {
  const corpus = await loadSolverGoldenCorpus();
  const vite = await createServer({
    appType: 'custom',
    logLevel: 'error',
    server: { middlewareMode: true },
  });

  try {
    const pipeline = await vite.ssrLoadModule('/src/lib/pdf/index.ts') as SolverPdfPipeline;
    const questionPaperResults: Array<{
      paper: SolverGoldenPaper;
      checks: SolverCorpusCheck[];
    }> = [];
    for (const paper of corpus.papers) {
      questionPaperResults.push({
        paper,
        checks: await auditQuestionPaper(paper, cacheDir, pipeline),
      });
    }

    // pdfjs-serverless bundles a different PDF.js release and installs its
    // worker globally. Load it only after every browser-pipeline PDF is done,
    // otherwise its worker can be paired with the app's newer PDF.js API.
    let edgePdfJs: ServerPdfJs;
    try {
      edgePdfJs = await import(pathToFileURL(EDGE_PDFJS_PATH).href) as ServerPdfJs;
    } catch (error) {
      throw new Error(
        'pdfjs-serverless is missing; run npm ci --prefix supabase/functions/fetch-pdf',
        { cause: error },
      );
    }

    const papers: SolverPaperAudit[] = [];
    for (const result of questionPaperResults) {
      const msBytes = await readPinnedSource(cacheDir, result.paper.sources.markScheme);
      const answerRows = await getAnswersFromPDF(edgePdfJs, exactArrayBuffer(msBytes));
      const answerKey = answerRows?.map((row) => row.answer.trim()).join('') ?? '';
      result.checks.push(exactCheck(
        'ms.answer-key',
        answerKey,
        result.paper.expected.answerKey,
      ));
      papers.push({
        ...result,
        classified: classifySolverCorpusChecks(result.checks, result.paper.knownFailures),
      });
    }

    return {
      papers,
      checkCount: papers.reduce((sum, result) => sum + result.checks.length, 0),
      knownFailureCount: papers.reduce(
        (sum, result) => sum + result.classified.knownFailures.length,
        0,
      ),
      unexpectedFailureCount: papers.reduce(
        (sum, result) => sum + result.classified.unexpectedFailures.length,
        0,
      ),
      unexpectedPassCount: papers.reduce(
        (sum, result) => sum + result.classified.unexpectedPasses.length,
        0,
      ),
    };
  } finally {
    await vite.close();
  }
}

function printAudit(audit: SolverCorpusAudit): void {
  for (const result of audit.papers) {
    const known = result.classified.knownFailures.length;
    const regressions = result.classified.unexpectedFailures.length;
    const changed = result.classified.unexpectedPasses.length;
    const status = regressions > 0 || changed > 0
      ? 'FAIL'
      : known > 0 ? 'KNOWN FAIL' : 'PASS';
    console.log(`${status.padEnd(10)} ${result.paper.paperId} (${result.checks.length} checks)`);

    for (const check of result.classified.knownFailures) {
      const reason = result.paper.knownFailures.find((failure) => failure.check === check.check)?.reason;
      console.log(`  known      ${check.check}: ${check.detail}${reason ? ` — ${reason}` : ''}`);
    }
    for (const check of result.classified.unexpectedFailures) {
      console.log(`  regression ${check.check}: ${check.detail}`);
    }
    for (const check of result.classified.unexpectedPasses) {
      console.log(`  review     ${check.check}: now passes; remove its known-failure declaration after review`);
    }
  }

  console.log(
    `\n${audit.papers.length} papers; ${audit.checkCount} checks; `
    + `${audit.knownFailureCount} known failures; `
    + `${audit.unexpectedFailureCount} regressions; `
    + `${audit.unexpectedPassCount} changed expectations`,
  );
}

const invokedPath = process.argv[1] ? pathToFileURL(resolve(process.argv[1])).href : '';
if (import.meta.url === invokedPath) {
  auditSolverGoldenCorpus()
    .then((audit) => {
      printAudit(audit);
      if (audit.unexpectedFailureCount > 0 || audit.unexpectedPassCount > 0) {
        process.exitCode = 1;
      }
    })
    .catch((error) => {
      console.error(error instanceof Error ? error.message : String(error));
      process.exitCode = 1;
    });
}
