// ==========================================================================
//
// The contract between the `fetch-pdf` Supabase edge function and the client.
//
// This contract was previously unwritten on both sides: the edge function
// returns an untyped JSON object, and MCQNav declared the result as
// `Promise<{ answers: any; ... }>`. So the mark-scheme rows - the thing every
// mark, every accuracy figure and the trusted answer-key install depends on -
// flowed through the app as `any`.
//
// Keep this in step with supabase/functions/fetch-pdf/index.ts.
// ==========================================================================

import type { TableRow } from '@/lib/processing/processingTypes';

/**
 * Metadata encoded beside the binary PDF in the multipart Edge response.
 */
export interface FetchPdfMetadata {
  /** Parsed mark-scheme rows, or null when the table could not be read. */
  answers: TableRow[] | null;
  /** Whether the server installed the fresh key into authoritative storage. */
  answerKey: {
    persisted: boolean;
    error?: string;
  };
}

/** What getPDF() hands back to the component after decoding the response. */
export interface LoadedPaper {
  answers: TableRow[] | null;
  pdfBytes: Uint8Array;
  /** Object URL for the blob; revoke it when the attempt ends. */
  pdfUrl: string;
  /** False means the paper is usable as practice but must not enter history. */
  answerKeyPersisted: boolean;
  answerKeyError?: string;
}

/** Request body the edge function expects. */
export interface FetchPdfRequest {
  /** Paper schema string, e.g. '0625_s25_22'. */
  schema: string;
}
