// ==========================================================================
//
// Removes background declarations from an inline `style` string.
//
// Extracted from MCQNav's injectStyles() so the one property that matters can
// be tested without a DOM: IDEMPOTENCE. This runs inside a MutationObserver
// that watches the `style` attribute, and the observer's handler writes that
// same attribute back. setAttribute() emits a mutation record even when the
// value is identical, so if this function is not idempotent - if feeding its
// own output back produces a different string - the observer re-fires forever
// and pins the main thread at 100% CPU.
// ==========================================================================

/**
 * @param style the current value of an element's `style` attribute
 * @returns the cleaned declaration string, or null when nothing is left and
 *          the attribute should be removed entirely. Returns the input
 *          UNCHANGED (same string) when there is nothing to strip, so callers
 *          can skip the write with a cheap `!==` check.
 */
export function stripInlineBackground(style: string): string | null {
  const parts = style
    .split(';')
    .map((p) => p.trim())
    .filter(
      (p) => p.length > 0 && !/^\s*(background|background-image|background-color)\s*:/i.test(p),
    );

  if (parts.length === 0) return null;

  // the join normalises separators to '; '. That normalisation is exactly
  // why the caller MUST compare before writing - on a style string written as
  // 'a:1;b:2' the output differs from the input on the first pass even though
  // no background was present. It converges after one pass, which is what
  // makes the fixed point reachable.
  return parts.join('; ');
}
