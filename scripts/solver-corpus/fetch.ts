// ==========================================================================
//
// Fetches the checksum-pinned solver golden corpus into an ignored local cache.
// ==========================================================================

import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, stat, unlink, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {
  loadSolverGoldenCorpus,
  type SolverCorpusSource,
} from './manifest.ts';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
export const DEFAULT_SOLVER_CORPUS_CACHE = resolve(
  SCRIPT_DIR,
  '../../tests/fixtures/solver-corpus/cache',
);
const FETCH_DELAY_MS = 1000;

export function solverCorpusSourceUrl(baseUrl: string, source: SolverCorpusSource): string {
  return `${baseUrl.replace(/\/$/, '')}/${source.file}`;
}

export function verifySolverCorpusSource(
  bytes: Uint8Array,
  expected: SolverCorpusSource,
): string | null {
  if (bytes.byteLength !== expected.bytes) {
    return `${expected.file}: byte count ${bytes.byteLength}, expected ${expected.bytes}`;
  }
  const actualHash = createHash('sha256').update(bytes).digest('hex');
  if (actualHash !== expected.sha256) {
    return `${expected.file}: SHA-256 ${actualHash}, expected ${expected.sha256}`;
  }
  if (bytes.byteLength < 5 || new TextDecoder().decode(bytes.subarray(0, 5)) !== '%PDF-') {
    return `${expected.file}: response is not a PDF`;
  }
  return null;
}

async function readVerified(path: string, source: SolverCorpusSource): Promise<boolean> {
  try {
    const info = await stat(path);
    if (!info.isFile()) return false;
    const bytes = new Uint8Array(await readFile(path));
    const error = verifySolverCorpusSource(bytes, source);
    if (error) throw new Error(error);
    return true;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return false;
    throw error;
  }
}

async function fetchSource(
  baseUrl: string,
  source: SolverCorpusSource,
  cacheDir: string,
): Promise<void> {
  const output = resolve(cacheDir, source.file);
  if (await readVerified(output, source)) {
    console.log(`cached  ${source.file}`);
    return;
  }

  const response = await fetch(solverCorpusSourceUrl(baseUrl, source), {
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; CambridgeParser corpus validator)',
      Accept: 'application/pdf,*/*;q=0.8',
    },
    redirect: 'manual',
  });
  const contentType = response.headers.get('content-type') ?? '';
  if (response.status !== 200 || !contentType.includes('pdf')) {
    throw new Error(`${source.file}: HTTP ${response.status}, content-type ${contentType || '(none)'}`);
  }

  const bytes = new Uint8Array(await response.arrayBuffer());
  const verificationError = verifySolverCorpusSource(bytes, source);
  if (verificationError) throw new Error(verificationError);

  const partial = `${output}.part`;
  await writeFile(partial, bytes);
  try {
    await rename(partial, output);
  } catch (error) {
    await unlink(partial).catch(() => undefined);
    throw error;
  }
  console.log(`fetched ${source.file}`);
}

export async function fetchSolverGoldenCorpus(
  cacheDir = DEFAULT_SOLVER_CORPUS_CACHE,
): Promise<void> {
  const corpus = await loadSolverGoldenCorpus();
  await mkdir(cacheDir, { recursive: true });

  let madeNetworkRequest = false;
  for (const paper of corpus.papers) {
    for (const source of [paper.sources.questionPaper, paper.sources.markScheme]) {
      const output = resolve(cacheDir, source.file);
      const cached = await readVerified(output, source);
      if (cached) {
        console.log(`cached  ${source.file}`);
        continue;
      }
      if (madeNetworkRequest) {
        await new Promise((done) => setTimeout(done, FETCH_DELAY_MS));
      }
      await fetchSource(corpus.sourceBaseUrl, source, cacheDir);
      madeNetworkRequest = true;
    }
  }
}

const invokedPath = process.argv[1] ? pathToFileURL(resolve(process.argv[1])).href : '';
if (import.meta.url === invokedPath) {
  fetchSolverGoldenCorpus().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
