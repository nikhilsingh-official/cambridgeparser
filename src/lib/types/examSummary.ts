// ==========================================================================
//
// The result summary shown on the end-exam screen.
//
// Kept as a pure function over data the client already has at endExam():
// `getQuestionsAnalytics` computes qCorrect per question, and the mark-scheme
// rows carry per-question marks. So the screen can render immediately without
// waiting on a Supabase round trip - which also means it still works when the
// attempt failed to persist.
//
// The DATABASE remains the authority on correctness (the
// set_question_correctness trigger). This is a local view of the same facts for
// immediate feedback; if the two ever disagree, the database is right.
// ==========================================================================

import type { QuestionsAnalytics, TableRow } from '@/lib/processing/processingTypes';
import { OPTION_LETTERS, type OptionLetter } from './enums';

/** How one question turned out. */
export const QuestionOutcome = {
  Correct: 'correct',
  Incorrect: 'incorrect',
  Unanswered: 'unanswered',
} as const;
export type QuestionOutcome = typeof QuestionOutcome[keyof typeof QuestionOutcome];

/** One row of the per-question breakdown grid. */
export interface QuestionResult {
  questionNumber: number;
  outcome: QuestionOutcome;
  selected: OptionLetter | null;
  correct: OptionLetter | null;
  marks: number;
  marksAwarded: number;
  /** Seconds, as accumulated by the focus-area timer. */
  timeSpent: number;
  /** Fast, no eliminations, no real interaction - probably not a decision. */
  wasGuess: boolean;
}

/** Everything the end screen renders. */
export interface ExamSummary {
  paperId: string;
  marksAwarded: number;
  marksTotal: number;
  /** 0..100, rounded to one decimal. */
  percentage: number;
  correctCount: number;
  incorrectCount: number;
  unansweredCount: number;
  questionCount: number;
  /** Whole attempt, milliseconds. */
  durationMs: number;
  /** Mean seconds per question, over answered questions only. */
  averageTimePerQuestion: number;
  /** Correct answers that look like lucky guesses - they flatter the score. */
  luckyGuessCount: number;
  results: QuestionResult[];
}

// same rule as v_question_flags in schema.sql - fast, no eliminations, and
// essentially no interaction. Kept in step with the SQL deliberately; if you
// tune one, tune the other.
const GUESS_TIME_RATIO = 0.4;
const GUESS_MAX_DEPTH = 1;

function medianOf(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? ((sorted[mid - 1] ?? 0) + (sorted[mid] ?? 0)) / 2
    : (sorted[mid] ?? 0);
}

function asOptionLetter(value: string | undefined | null): OptionLetter | null {
  if (!value) return null;
  const upper = value.trim().toUpperCase();
  return (OPTION_LETTERS as readonly string[]).includes(upper)
    ? (upper as OptionLetter)
    : null;
}

/**
 * Build the end-screen summary.
 *
 * @param paperId     the Cambridge schema string, e.g. '0625_s25_22'
 * @param analytics   output of getQuestionsAnalytics (carries qCorrect)
 * @param answers     mark-scheme rows from the fetch-pdf edge function
 * @param durationMs  whole-attempt elapsed time
 */
export function buildExamSummary(
  paperId: string,
  analytics: QuestionsAnalytics,
  answers: TableRow[] | null,
  durationMs: number,
): ExamSummary {
  const answerByQuestion = new Map<number, TableRow>(
    (answers ?? []).map((row) => [row.question, row]),
  );

  const medianTime = medianOf(analytics.map((q) => q.time ?? 0));

  const results: QuestionResult[] = analytics.map((q) => {
    const row = answerByQuestion.get(q.questionNumber);
    const parsedMarks = Number.parseInt(String(row?.marks ?? '1'), 10);
    const marks = Number.isFinite(parsedMarks) && parsedMarks > 0 ? parsedMarks : 1;

    const selected = asOptionLetter(q.selectedOption);
    const correct = asOptionLetter(row?.answer);

    const outcome: QuestionOutcome = selected === null
      ? QuestionOutcome.Unanswered
      : q.qCorrect
        ? QuestionOutcome.Correct
        : QuestionOutcome.Incorrect;

    const timeSpent = q.time ?? 0;
    const wasGuess =
      outcome !== QuestionOutcome.Unanswered
      && medianTime > 0
      && timeSpent < GUESS_TIME_RATIO * medianTime
      && (q.explorationDepth ?? 0) <= GUESS_MAX_DEPTH
      && (q.eliminatedOptions?.length ?? 0) === 0;

    return {
      questionNumber: q.questionNumber,
      outcome,
      selected,
      correct,
      marks,
      marksAwarded: outcome === QuestionOutcome.Correct ? marks : 0,
      timeSpent,
      wasGuess,
    };
  });

  const marksTotal = results.reduce((sum, r) => sum + r.marks, 0);
  const marksAwarded = results.reduce((sum, r) => sum + r.marksAwarded, 0);
  const correctCount = results.filter((r) => r.outcome === QuestionOutcome.Correct).length;
  const incorrectCount = results.filter((r) => r.outcome === QuestionOutcome.Incorrect).length;
  const unansweredCount = results.filter((r) => r.outcome === QuestionOutcome.Unanswered).length;
  const answered = results.filter((r) => r.outcome !== QuestionOutcome.Unanswered);

  return {
    paperId,
    marksAwarded,
    marksTotal,
    percentage: marksTotal > 0
      ? Math.round((marksAwarded / marksTotal) * 1000) / 10
      : 0,
    correctCount,
    incorrectCount,
    unansweredCount,
    questionCount: results.length,
    durationMs,
    averageTimePerQuestion: answered.length > 0
      ? answered.reduce((sum, r) => sum + r.timeSpent, 0) / answered.length
      : 0,
    luckyGuessCount: results.filter(
      (r) => r.wasGuess && r.outcome === QuestionOutcome.Correct,
    ).length,
    results,
  };
}

/** `1h 04m 12s` / `4m 12s` / `12s`, for the duration tile. */
export function formatDuration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m ${String(s).padStart(2, '0')}s`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}
