// ============================================================================
//
// Browser-side validator for the multipart fetch-pdf response.
// ============================================================================

import type { TableRow } from '../processing/processingTypes';
import type { FetchPdfMetadata } from '../types/fetchPdf';
import { validateAnswerKey } from './validateAnswerKey.ts';

type AnswerKeyPersistence = FetchPdfMetadata['answerKey'];

export interface DecodedFetchPdfResponse {
  pdfBytes: Uint8Array;
  answers: TableRow[];
  answerKey: AnswerKeyPersistence;
}

function parseAnswerKey(value: unknown): AnswerKeyPersistence | null {
  if (!value || typeof value !== 'object') return null;
  const candidate = value as Record<string, unknown>;
  if (typeof candidate.persisted !== 'boolean') return null;
  if (candidate.error !== undefined && typeof candidate.error !== 'string') return null;
  return candidate.error === undefined
    ? { persisted: candidate.persisted }
    : { persisted: candidate.persisted, error: candidate.error };
}

/** Decode only the FormData shape produced by Supabase FunctionsClient. */
export async function decodeFetchPdfResponse(value: unknown): Promise<DecodedFetchPdfResponse> {
  if (!(value instanceof FormData)) {
    throw new Error('The paper service returned an unsupported response format');
  }

  const pdfPart = value.get('pdf');
  if (!(pdfPart instanceof Blob)) {
    throw new Error('The paper service response is missing its PDF part');
  }

  const metadataPart = value.get('metadata');
  if (typeof metadataPart !== 'string') {
    throw new Error('The paper service response is missing its metadata');
  }

  let rawMetadata: unknown;
  try {
    rawMetadata = JSON.parse(metadataPart);
  } catch {
    throw new Error('The paper service returned malformed metadata');
  }
  if (!rawMetadata || typeof rawMetadata !== 'object') {
    throw new Error('The paper service returned malformed metadata');
  }

  const metadata = rawMetadata as Record<string, unknown>;
  const answers = validateAnswerKey(metadata.answers);
  if (!answers) throw new Error('The mark scheme did not contain a complete answer key');

  const answerKey = parseAnswerKey(metadata.answerKey);
  if (!answerKey) throw new Error('The paper service returned invalid persistence metadata');

  const pdfBytes = new Uint8Array(await pdfPart.arrayBuffer());
  const signature = new TextDecoder().decode(pdfBytes.subarray(0, 5));
  if (signature !== '%PDF-') throw new Error('The paper service returned invalid PDF bytes');

  return { pdfBytes, answers, answerKey };
}
