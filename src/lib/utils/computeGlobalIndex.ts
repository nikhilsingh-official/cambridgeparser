export function computeGlobalIndex<T>(
  document: T[][],
  pageIndex: number,
  segmentIndex: number
): number {
  let count = 0;

  for (let i = 0; i < pageIndex; i++) {
    const page = document[i];
    if (page) count += page.length;
  }

  return count + segmentIndex + 1;
}