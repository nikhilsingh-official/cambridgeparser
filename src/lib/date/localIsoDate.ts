// ==========================================================================
//
// A calendar date in an explicit IANA timezone. Date#toISOString() is always
// UTC, so slicing it gives the wrong "today" near midnight for most users.
// ==========================================================================

import type { IsoDate } from '@/lib/types/database';

export function localIsoDate(
  when = new Date(),
  timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
): IsoDate {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(when);

  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find(part => part.type === type)?.value;
  const year = value('year');
  const month = value('month');
  const day = value('day');
  if (!year || !month || !day) throw new Error('Could not format local date');
  return `${year}-${month}-${day}`;
}
