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

  return unwrap<QuestionFlagsView>(
    'fetchQuestionFlags',
    applyAttemptFilter(
      supabase.from('v_question_flags').select('*'),
      userId,
      narrowed,
    ),
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

export function summariseFlags(flags: QuestionFlagsView[]): FocusTotals {
  const guesses = flags.filter(f => f.is_guess);
  const guessedCorrect = guesses.filter(f => f.is_correct === true).length;

  return {
    questions: flags.length,
    overconfident: flags.filter(f => f.is_overconfident === true).length,
    underconfident: flags.filter(f => f.is_underconfident === true).length,
    guesses: guesses.length,
    guessAccuracy: guesses.length > 0 ? guessedCorrect / guesses.length : null,
    // hesitation is not on this view; the tile is wired when the scatter
    // query below supplies it. Null keeps the tile honestly empty meanwhile.
    medianHesitationMs: null,
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
