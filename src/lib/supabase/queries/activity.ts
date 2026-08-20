// ==========================================================================
// Reads for the ENGAGEMENT section: calendar heatmap, session line, streaks.
// ==========================================================================

import type { DailyActivityView, Db, HourOfDayView, IsoDate } from '@/lib/types/database';
import { unwrap } from './core';

/**
 * Daily totals for the calendar heatmap and the study-time line.
 *
 * no subject filter. v_daily_activity aggregates across subjects by design -
 * "did I study today" is not a per-subject question, and filtering it by subject
 * would make the heatmap show gaps on days the student did work.
 */
export async function fetchDailyActivity(
  supabase: Db,
  userId: string,
  from?: IsoDate,
  to?: IsoDate,
): Promise<DailyActivityView[]> {
  let query = supabase
    .from('v_daily_activity')
    .select('*')
    .eq('user_id', userId);

  if (from) query = query.gte('local_date', from);
  if (to)   query = query.lte('local_date', to);

  return unwrap<DailyActivityView>(
    'fetchDailyActivity',
    query.order('local_date', { ascending: true }),
  );
}

/** 24 bins of local-hour activity, for the peak-solving-hour polar chart. */
export async function fetchHourOfDay(
  supabase: Db,
  userId: string,
): Promise<HourOfDayView[]> {
  return unwrap<HourOfDayView>(
    'fetchHourOfDay',
    supabase
      .from('v_hour_of_day')
      .select('*')
      .eq('user_id', userId)
      .order('local_hour', { ascending: true }),
  );
}

/**
 * Current and longest consecutive-day practice streaks.
 *
 * computed here rather than in SQL. The window-function version (a gaps-
 * and-islands query over local_date) is genuinely harder to read and to change,
 * and this input is one row per active day - tens to hundreds, not thousands.
 *
 * `today` is passed in rather than read from the clock so this is testable and
 * so the caller can supply the user's LOCAL today. Using the browser's date
 * here would break the streak for anyone whose timezone has already rolled over.
 */
export function computeStreaks(
  activity: DailyActivityView[],
  today: IsoDate,
): { current: number; longest: number } {
  if (activity.length === 0) return { current: 0, longest: 0 };

  const days = [...new Set(activity.map(a => a.local_date))].sort();

  const dayNumber = (iso: IsoDate): number =>
    Math.floor(Date.parse(`${iso}T00:00:00Z`) / 86_400_000);

  let longest = 1;
  let run = 1;
  for (let i = 1; i < days.length; i++) {
    // non-null asserted - both indices are inside the array by construction.
    const gap = dayNumber(days[i]!) - dayNumber(days[i - 1]!);
    run = gap === 1 ? run + 1 : 1;
    if (run > longest) longest = run;
  }

  // the streak survives if the last active day was today OR yesterday.
  // Ending it at midnight would show "0 day streak" to someone who simply has
  // not started yet this morning, which is both wrong and demoralising.
  const lastGap = dayNumber(today) - dayNumber(days[days.length - 1]!);
  let current = 0;
  if (lastGap <= 1) {
    current = 1;
    for (let i = days.length - 1; i > 0; i--) {
      if (dayNumber(days[i]!) - dayNumber(days[i - 1]!) === 1) current++;
      else break;
    }
  }

  return { current, longest };
}
