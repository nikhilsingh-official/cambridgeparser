// ==========================================================================
// Reads for the FOCUS section: calibration, the time/correctness scatter, and
// the six-tile metric bar. See docs/stats_page_design.md §3.1.
// ==========================================================================

import type {
  Db,
  QuestionFlagsView,
} from '@/lib/types/database';
import { applyAttemptFilter, unwrap, type StatsFilter } from './core';
import { fetchCountedPages } from './pagination';
import { isGuess, isOverconfident, isUnderconfident } from '@/lib/stats/model';
import {
  summariseAnswerChangeRows,
  type AnswerChangeSummary,
  type AnswerChangeVerdict,
} from '@/lib/stats/filterScope';

export type { AnswerChangeSummary } from '@/lib/stats/filterScope';

/**
 * Per-question flags, filtered to the user.
 *
 * v_question_flags gained user_id/subject_code/local_date specifically so
 * this function could exist. Without them the view could only be filtered by
 * exam_attempt_id, which meant either N round trips or - with RLS deferred -
 * pulling every user's questions to the browser.
 */
export async function fetchQuestionFlags(
  supabase: Db,
  userId: string,
  filter: StatsFilter = {},
): Promise<QuestionFlagsView[]> {
  // exam_year/series/variant are not on this view, so only the columns it
  // actually exposes are applied. Passing the full filter would silently
  // generate a predicate on a missing column and fail at runtime.
  const narrowed: StatsFilter = {
    subjectCodes: filter.subjectCodes,
    from: filter.from,
    to: filter.to,
  };

  // PAGINATED, deliberately. PostgREST truncates at its max_rows cap.
  // The local cap is 10,000, while exact-count pagination also stays correct
  // against a hosted project configured lower. This view passed 1,000 rows
  // after about 25 papers and previously reported that truncated subset as fact.
  const query = applyAttemptFilter(
    supabase.from('v_question_flags').select('*', { count: 'exact' }),
    userId,
    narrowed,
  ).order('question_attempt_id', { ascending: true });

  return fetchCountedPages<QuestionFlagsView>(
    'fetchQuestionFlags',
    10_000,
    (from, to) => query.range(from, to),
  );
}

/** The six tiles under the charts in the focus section. */
export interface FocusTotals {
  questions: number;
  overconfident: number;
  underconfident: number;
  guesses: number;
  /** 0..1 - how often a guess happened to be right. Null when there are none. */
  guessAccuracy: number | null;
  /** Median, not mean - hesitation has a long right tail. Milliseconds. */
  medianHesitationMs: number | null;
}

/** Median of an unsorted list, or null when empty. */
function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1]! + sorted[mid]!) / 2 : sorted[mid]!;
}

// the three rules moved out of v_question_flags and into model.ts
// (migration 00000000000007). This function used to read boolean columns the
// database had already decided; it now applies the same rules the rest of the
// page's claims come from, so a retune is one edit rather than a migration.
export function summariseFlags(flags: QuestionFlagsView[]): FocusTotals {
  const guesses = flags.filter(isGuess);
  const guessedCorrect = guesses.filter(f => f.is_correct === true).length;

  return {
    questions: flags.length,
    overconfident: flags.filter(isOverconfident).length,
    underconfident: flags.filter(isUnderconfident).length,
    guesses: guesses.length,
    guessAccuracy: guesses.length > 0 ? guessedCorrect / guesses.length : null,
    // median, not mean - hesitation has a long right tail (one question
    // stared at for four minutes would drag a mean somewhere no question
    // actually was).
    medianHesitationMs: median(flags.map(f => f.hesitation_ms).filter((n): n is number => n != null)),
  };
}

/**
 * Points for the time-vs-correctness scatter.
 *
 * reads question_attempts joined to question_metrics rather than a view,
 * because no view carries both time_spent_ms and confidence at question grain
 * alongside exploration_depth. PostgREST embedding does the join.
 */
export interface ScatterPoint {
  timeSpentMs: number;
  confidence: number | null;
  isCorrect: boolean | null;
  explorationDepth: number;
  questionNumber: number;
  hesitationMs: number | null;
}

interface ScatterRow {
  question_number: number;
  time_spent_ms: number;
  hesitation_ms: number | null;
  exploration_depth: number;
  is_correct: boolean | null;
  // PostgREST returns an embedded to-one relation as an object, but as an
  // ARRAY when it cannot prove uniqueness. question_metrics is keyed by
  // (question_attempt_id, metrics_version) so both shapes are possible here
  // depending on how the FK is introspected - handle both rather than guess.
  question_metrics: { confidence: number }[] | { confidence: number } | null;
}

export async function fetchScatterPoints(
  supabase: Db,
  userId: string,
  filter: StatsFilter = {},
): Promise<ScatterPoint[]> {
  const attempts = await unwrap<{ id: string }>(
    'fetchScatterPoints/attempts',
    applyAttemptFilter(
      supabase.from('v_attempt_summary').select('id'),
      userId,
      filter,
    ),
  );
  if (attempts.length === 0) return [];

  const rows = await unwrap<ScatterRow>(
    'fetchScatterPoints',
    supabase
      .from('question_attempts')
      .select(
        'question_number, time_spent_ms, hesitation_ms, exploration_depth, is_correct, question_metrics(confidence)',
      )
      .in('exam_attempt_id', attempts.map(a => a.id)),
  );

  return rows.map(r => ({
    questionNumber: r.question_number,
    timeSpentMs: r.time_spent_ms,
    hesitationMs: r.hesitation_ms,
    explorationDepth: r.exploration_depth,
    isCorrect: r.is_correct,
    confidence: Array.isArray(r.question_metrics)
      ? r.question_metrics[0]?.confidence ?? null
      : r.question_metrics?.confidence ?? null,
  }));
}

// ==========================================================================
// answer-change quality. The metric docs/roadmap.md B6 called the highest
// value unbuilt one - `attempt_events` has recorded every option transition
// since it existed, and nothing read it.
// ==========================================================================

export async function fetchAnswerChanges(
  supabase: Db,
  userId: string,
  filter: Pick<StatsFilter, 'subjectCodes' | 'from' | 'to'> = {},
): Promise<AnswerChangeSummary | null> {
  // the summary view is all-time and cannot be filtered. Read the compact
  // verdict rows instead, apply the same subject/date scope as the rest of the
  // solver page, then aggregate the handful of counters in the browser.
  const query = applyAttemptFilter(
    supabase
      .from('v_answer_changes')
      .select('exam_attempt_id, question_number, elapsed_ms, verdict', { count: 'exact' }),
    userId,
    filter,
  )
    .order('exam_attempt_id', { ascending: true })
    .order('question_number', { ascending: true })
    .order('elapsed_ms', { ascending: true });
  const rows = await fetchCountedPages<{
    exam_attempt_id: string;
    question_number: number;
    elapsed_ms: number;
    verdict: AnswerChangeVerdict;
  }>(
    'fetchAnswerChanges',
    10_000,
    (from, to) => query.range(from, to),
  );
  return summariseAnswerChangeRows(rows);
}
