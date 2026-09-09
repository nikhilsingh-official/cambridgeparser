// ============================================================================
//
// Contract tests for the binary fetch-pdf HTTP response and browser decoder.
// ============================================================================

import assert from 'node:assert/strict';
import test from 'node:test';
import { FunctionsClient } from '@supabase/functions-js';
import {
  createFetchPdfJsonResponse,
  createFetchPdfPreflightResponse,
  createFetchPdfResponse,
} from '../supabase/functions/fetch-pdf/paperResponse.ts';
import { decodeFetchPdfResponse } from '../src/lib/pdf/decodeFetchPdfResponse.ts';

const metadata = {
  answers: [{ question: 1, answer: 'B', marks: '1', page: 2, y: 140 }],
  answerKey: { persisted: true },
};

test('fetch-pdf accepts the browser CORS preflight used by Supabase FunctionsClient', () => {
  const request = new Request('https://example.test/functions/v1/fetch-pdf', {
    method: 'OPTIONS',
    headers: {
      Origin: 'https://www.cambridgeparser.com',
      'Access-Control-Request-Method': 'POST',
      'Access-Control-Request-Headers': 'authorization,apikey,content-type,x-client-info',
    },
  });

  const response = createFetchPdfPreflightResponse(request);
  assert.ok(response);
  assert.equal(response.status, 204);
  assert.equal(response.headers.get('access-control-allow-origin'), '*');
  assert.match(response.headers.get('access-control-allow-methods') ?? '', /POST/);
  assert.match(response.headers.get('access-control-allow-headers') ?? '', /authorization/);
  assert.match(response.headers.get('access-control-allow-headers') ?? '', /x-client-info/);
});

test('fetch-pdf error responses retain CORS headers', async () => {
  const response = createFetchPdfJsonResponse(405, { error: 'Method not allowed' });
  assert.equal(response.status, 405);
  assert.equal(response.headers.get('access-control-allow-origin'), '*');
  assert.deepEqual(await response.json(), { error: 'Method not allowed' });
});

test('representative two-megabyte paper round-trips with compact multipart overhead', async () => {
  // deterministic tracked input keeps this mandatory contract test runnable
  // on clean clones; the real largest corpus PDF is reserved for local E2E.
  const pdf = Buffer.alloc(2_006_131, 0x61);
  pdf.write('%PDF-1.7\n', 0, 'ascii');
  const pdfArrayBuffer = pdf.buffer.slice(
    pdf.byteOffset,
    pdf.byteOffset + pdf.byteLength,
  ) as ArrayBuffer;
  const response = createFetchPdfResponse('9700_w25_13', pdfArrayBuffer, metadata);

  assert.match(response.headers.get('content-type') ?? '', /^multipart\/form-data; boundary=/);
  const wireBytes = (await response.clone().arrayBuffer()).byteLength;
  assert.ok(wireBytes < pdf.byteLength * 1.01, 'multipart overhead must stay below 1%');

  // exercise the installed client rather than imitating its Content-Type
  // branch; this is the exact handoff MCQNav receives in production.
  const client = new FunctionsClient('https://example.test/functions/v1', {
    customFetch: async () => createFetchPdfResponse('9700_w25_13', pdfArrayBuffer, metadata),
  });
  const invocation = await client.invoke('fetch-pdf', { body: { schema: '9700_w25_13' } });
  assert.equal(invocation.error, null);
  const decoded = await decodeFetchPdfResponse(invocation.data);
  assert.deepEqual(decoded.answers, metadata.answers);
  assert.deepEqual(decoded.answerKey, metadata.answerKey);
  assert.deepEqual(Buffer.from(decoded.pdfBytes), pdf);
});

test('the browser decoder rejects incomplete multipart responses', async () => {
  const missingPdf = new FormData();
  missingPdf.set('metadata', JSON.stringify(metadata));
  await assert.rejects(decodeFetchPdfResponse(missingPdf), /PDF part/);

  const invalidKey = new FormData();
  invalidKey.set('pdf', new Blob(['%PDF-test'], { type: 'application/pdf' }), 'paper.pdf');
  invalidKey.set('metadata', JSON.stringify({ ...metadata, answers: [] }));
  await assert.rejects(decodeFetchPdfResponse(invalidKey), /complete answer key/);
});
