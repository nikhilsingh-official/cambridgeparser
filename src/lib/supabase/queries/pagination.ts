// ==========================================================================
// Count-aware PostgREST pagination that remains correct when the server's
// max_rows setting is lower than the range requested by the browser.
// ==========================================================================

interface PageError {
  message: string;
  hint?: string | null;
}

export interface CountedPage<T> {
  data: T[] | null;
  error: PageError | null;
  count: number | null;
}

export async function fetchCountedPages<T>(
  context: string,
  requestedPageSize: number,
  fetchPage: (from: number, to: number) => PromiseLike<CountedPage<T>>,
): Promise<T[]> {
  if (!Number.isInteger(requestedPageSize) || requestedPageSize < 1) {
    throw new Error(`${context} page size must be a positive integer`);
  }

  const rows: T[] = [];
  while (true) {
    const from = rows.length;
    const page = await fetchPage(from, from + requestedPageSize - 1);
    if (page.error) {
      console.error(`[queries/${context}]`, page.error);
      throw new Error(
        `${context} failed: ${page.error.message}`
          + (page.error.hint ? ` (hint: ${page.error.hint})` : ''),
      );
    }

    const pageRows = page.data ?? [];
    rows.push(...pageRows);
    if (pageRows.length === 0 || (page.count !== null && rows.length >= page.count)) {
      return rows;
    }
  }
}
