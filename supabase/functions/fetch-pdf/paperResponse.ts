// ============================================================================
//
// Binary HTTP response contract shared by fetch-pdf and its contract tests.
// ============================================================================

export const FETCH_PDF_CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
} as const;

/** Answer the browser's preflight before normal method validation runs. */
export function createFetchPdfPreflightResponse(request: Request): Response | null {
  if (request.method !== 'OPTIONS') return null;
  return new Response(null, { status: 204, headers: FETCH_PDF_CORS_HEADERS });
}

/** Keep application errors readable by callers on a different origin. */
export function createFetchPdfJsonResponse(status: number, payload: unknown): Response {
  return Response.json(payload, {
    status,
    headers: {
      ...FETCH_PDF_CORS_HEADERS,
      'Content-Type': 'application/json',
    },
  });
}

/**
 * Return one invocation containing the PDF as binary and the small structured
 * payload as JSON. FormData owns Content-Type so its boundary always matches
 * the encoded body.
 */
export function createFetchPdfResponse(
  schema: string,
  pdf: ArrayBuffer,
  metadata: unknown,
  extraHeaders?: HeadersInit,
): Response {
  const formData = new FormData();
  formData.set(
    'pdf',
    new Blob([pdf], { type: 'application/pdf' }),
    `${schema}.pdf`,
  );
  formData.set('metadata', JSON.stringify(metadata));

  const headers = new Headers(FETCH_PDF_CORS_HEADERS);
  new Headers(extraHeaders).forEach((value, name) => headers.set(name, value));
  headers.delete('Content-Type');

  return new Response(formData, { status: 200, headers });
}
