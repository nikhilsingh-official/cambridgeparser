// ============================================================================
//
// Explicit viewport policy for desktop-only application routes.
// ============================================================================

export const MINIMUM_APP_WIDTH = 768;

/** Only explicitly supported routes remain available below the app breakpoint. */
export function shouldBlockMobileLayout(width: number, supportsNarrowViewport: boolean): boolean {
  return Number.isFinite(width) && width < MINIMUM_APP_WIDTH && !supportsNarrowViewport;
}
