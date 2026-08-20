// ==========================================================================
// Active goals - the markLine on the progress multiline, and the "Next Goal"
// card. The goals table has existed since the data-layer pass with nothing
// reading it.
// ==========================================================================

import type { Db, GoalRow } from '@/lib/types/database';
import { unwrap } from './core';

export async function fetchActiveGoals(
  supabase: Db,
  userId: string,
): Promise<GoalRow[]> {
  return unwrap<GoalRow>(
    'fetchActiveGoals',
    supabase
      .from('goals')
      .select('*')
      .eq('user_id', userId)
      .eq('active', true)
      .order('created_at', { ascending: false }),
  );
}
