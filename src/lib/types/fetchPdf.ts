// ==========================================================================
//
// The contract between the `fetch-pdf` Supabase edge function and the client.
//
// This contract was previously unwritten on both sides: the edge function
// returns an untyped JSON object, and MCQNav declared the result as
// `Promise<{ answers: any; ... }>`. So the mark-scheme rows - the thing every
// mark, every accuracy figure and the whole answer key cache depends on -
// flowed through the app as `any`.
//
// Keep this in step with supabase/functions/fetch-pdf/index.ts.
// ==========================================================================

import type { TableRow } from '@/lib/processing/processingTypes';

/**
 * Raw body returned by the edge function.
 *
 * `qp` is the question-paper PDF as a byte array. It is JSON, so the bytes
 * arrive as a plain number[] - which inflates a ~1 MB PDF to ~4 MB of text.
 * That inefficiency is pre-existing and tracked in FUTURE_WORK.md; the type
 * documents it rather than hiding it.
 *
 * The Record form is tolerated because JSON transports of typed arrays
 * sometimes arrive as `{"0": 37, "1": 80, ...}` rather than an array, and the
 * existing client already branches on that.
 */
export interface FetchPdfResponse {
  qp: number[] | Record<string, number>;
  /** Parsed mark-scheme rows, or null when the table could not be read. */
  answers: TableRow[] | null;
}

/** What getPDF() hands back to the component after decoding the response. */
export interface LoadedPaper {
  answers: TableRow[] | null;
  pdfBytes: Uint8Array;
  /** Object URL for the blob; revoke it when the attempt ends. */
  pdfUrl: string;
}

/** Request body the edge function expects. */
export interface FetchPdfRequest {
  /** Paper schema string, e.g. '0625_s25_22'. */
  schema: string;
}
