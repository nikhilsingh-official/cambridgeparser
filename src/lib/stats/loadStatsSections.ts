// ==========================================================================
// Runs each statistics section behind its own failure boundary so one broken
// view cannot erase otherwise valid panels.
// ==========================================================================

export interface StatsSectionResult<T> {
  data: T | null;
  error: string | null;
}

export async function loadStatsSections<K extends string, T>(
  loaders: Record<K, () => Promise<T>>,
): Promise<Record<K, StatsSectionResult<T>>> {
  const entries = Object.entries(loaders) as Array<[K, () => Promise<T>]>;
  const settled = await Promise.all(entries.map(async ([section, loader]) => {
    try {
      return [section, { data: await loader(), error: null }] as const;
    } catch (error) {
      return [section, {
        data: null,
        error: error instanceof Error ? error.message : String(error),
      }] as const;
    }
  }));

  return Object.fromEntries(settled) as Record<K, StatsSectionResult<T>>;
}
