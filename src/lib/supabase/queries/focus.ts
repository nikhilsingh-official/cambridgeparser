// ==========================================================================
// Reads for the FOCUS section: calibration, the time/correctness scatter, and
// the six-tile metric bar. See docs/stats_page_design.md §3.1.
// ==========================================================================

import type {
  CalibrationPointView,
  Db,
  QuestionFlagsView,
} from '@/lib/types/database';
import { applyAttemptFilter, unwrap, type StatsFilter } from './core';
import { fetchCountedPages } from './pagination';
import { isGuess, isOverconfident, isUnderconfident } from '@/lib/stats/model';

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

/**
 * The calibration curve.
 *
 * `buckets` re-bins the 10 deciles v_calibration_curve produces. At a few
 * hundred questions most deciles hold fewer than five rows and the curve is
 * noise dressed as insight - docs/stats_page_design.md §6. Re-binning client-side
 * keeps the view stable while letting the UI choose a resolution its sample
 * size can support.
 */
export interface CalibrationPoint {
  meanConfidence: number;
  observedAccuracy: number;
  questions: number;
  /** observedAccuracy - meanConfidence. Negative = overconfident. */
  gap: number;
}

export async function fetchCalibrationCurve(
  supabase: Db,
  userId: string,
  buckets = 5,
): Promise<CalibrationPoint[]> {
  const rows = await unwrap<CalibrationPointView>(
    'fetchCalibrationCurve',
    supabase
      .from('v_calibration_curve')
      .select('*')
      .eq('user_id', userId)
      .order('confidence_bucket', { ascending: true }),
  );

  if (rows.length === 0) return [];

  // weighted re-bin. Merging deciles means recombining WEIGHTED means -
  // averaging the decile averages would count a bucket of 2 questions as
  // heavily as one of 200.
  const merged = new Map<number, { conf: number; acc: number; n: number }>();
  for (const r of rows) {
    // width_bucket returns 1..10; map onto 0..buckets-1.
    const target = Math.min(
      buckets - 1,
      Math.floor(((r.confidence_bucket - 1) / 10) * buckets),
    );
    const cell = merged.get(target) ?? { conf: 0, acc: 0, n: 0 };
    cell.conf += r.mean_confidence * r.questions;
    cell.acc  += r.observed_accuracy * r.questions;
    cell.n    += r.questions;
    merged.set(target, cell);
  }

  return [...merged.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([, c]) => {
      const meanConfidence = c.conf / c.n;
      const observedAccuracy = c.acc / c.n;
      return {
        meanConfidence,
        observedAccuracy,
        questions: c.n,
        gap: observedAccuracy - meanConfidence,
      };
    });
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

export interface AnswerChangeSummary {
  changes: number;
  wrongToRight: number;
  rightToWrong: number;
  wrongToWrong: number;
  /** wrongToRight - rightToWrong. Marks that changing your mind won or cost. */
  netMarks: number;
}

export async function fetchAnswerChanges(
  supabase: Db,
  userId: string,
): Promise<AnswerChangeSummary | null> {
  const rows = await unwrap<{
    changes: number; wrong_to_right: number; right_to_wrong: number;
    wrong_to_wrong: number; net_marks: number;
  }>(
    'fetchAnswerChanges',
    supabase.from('v_answer_change_summary').select('*').eq('user_id', userId),
  );
  const row = rows[0];
  // Null rather than a row of zeros: a user who has never changed an answer has
  // no data here, which is a different statement from "changed 0 answers".
  if (!row || row.changes === 0) return null;
  return {
    changes: row.changes,
    wrongToRight: row.wrong_to_right,
    rightToWrong: row.right_to_wrong,
    wrongToWrong: row.wrong_to_wrong,
    netMarks: row.net_marks,
  };
}
