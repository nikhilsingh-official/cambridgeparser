// ==========================================================================
// Formatting shared by every tile and tooltip, so "72%" and "1h 04m" mean the
// same thing and round the same way everywhere on the page.
// ==========================================================================

/** Percentage from a 0-1 ratio. Null in, em dash out - never "NaN%". */
export function pct(ratio: number | null | undefined, digits = 0): string | null {
  if (ratio === null || ratio === undefined || !Number.isFinite(ratio)) return null;
  return `${(ratio * 100).toFixed(digits)}%`;
}

/** Compact duration: 45s, 12m, 1h 04m, 27h. */
export function duration(ms: number | null | undefined): string | null {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return null;
  const totalMinutes = Math.round(ms / 60000);
  if (totalMinutes < 1) return `${Math.round(ms / 1000)}s`;
  if (totalMinutes < 60) return `${totalMinutes}m`;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours >= 24) return `${hours}h`;
  return `${hours}h ${String(minutes).padStart(2, '0')}m`;
}

export function count(n: number | null | undefined): string | null {
  if (n === null || n === undefined || !Number.isFinite(n)) return null;
  return n.toLocaleString();
}

/** "14 Aug" - short enough for an axis label, unambiguous across months. */
export function shortDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

/**
 * A subject's display name, disambiguated by code only when it needs to be.
 *
 * Cambridge reuses names across qualifications: 0478 (IGCSE) and 9618 (A Level)
 * are both "Computer Science". The stats page showed one as the strongest
 * subject and the other as the weakest, which read as a bug in the page rather
 * than two different courses. Appending the code unconditionally would clutter
 * the common case, so it is appended only where the name is ambiguous within
 * the data actually on screen.
 */
export function subjectLabel(
  subject: { subject_code: string; subject_name?: string | null },
  all: { subject_code: string; subject_name?: string | null }[],
): string {
  const name = subject.subject_name ?? subject.subject_code;
  const sharesName = all.some(
    other => other.subject_code !== subject.subject_code
      && (other.subject_name ?? other.subject_code) === name,
  );
  return sharesName ? `${name} ${subject.subject_code}` : name;
}
