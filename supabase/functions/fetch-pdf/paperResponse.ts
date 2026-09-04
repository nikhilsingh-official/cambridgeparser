// ============================================================================
//
// Binary HTTP response contract shared by fetch-pdf and its contract tests.
// ============================================================================

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

  const headers = new Headers(extraHeaders);
  headers.delete('Content-Type');

  return new Response(formData, { status: 200, headers });
}
