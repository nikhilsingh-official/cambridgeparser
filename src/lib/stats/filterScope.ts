// ==========================================================================
// Pure aggregations used to make every solver statistics section describe the
// same already-filtered attempt/question set.
// ==========================================================================

import type {
  AttemptSummaryView,
  DailyActivityView,
  HourOfDayView,
  QuestionFlagsView,
  SubjectStatsView,
} from '@/lib/types/database';

export interface CalibrationPoint {
  meanConfidence: number;
  observedAccuracy: number;
  questions: number;
  /** observedAccuracy - meanConfidence. Negative means overconfident. */
  gap: number;
}

export interface AnswerChangeSummary {
  changes: number;
  wrongToRight: number;
  rightToWrong: number;
  wrongToWrong: number;
  netMarks: number;
}

export type AnswerChangeVerdict = 'wrong_to_right' | 'right_to_wrong' | 'wrong_to_wrong';

export function aggregateSubjectStats(attempts: AttemptSummaryView[]): SubjectStatsView[] {
  const grouped = new Map<string, SubjectStatsView>();
  for (const attempt of attempts) {
    const row = grouped.get(attempt.subject_code) ?? {
      user_id: attempt.user_id,
      subject_code: attempt.subject_code,
      subject_name: attempt.subject_name,
      attempts: 0,
      marks_awarded: 0,
      marks_total: 0,
      accuracy: null,
      total_time_ms: null,
      last_attempt_at: null,
      // these question-metric means are not displayed anywhere. They are
      // intentionally withheld rather than copied from an all-time view that
      // would violate the page filter.
      avg_confidence: null,
      avg_difficulty: null,
      avg_interest: null,
    };
    row.attempts += 1;
    row.marks_awarded += attempt.marks_awarded ?? 0;
    row.marks_total += attempt.marks_total ?? 0;
    if (attempt.duration_ms !== null) {
      row.total_time_ms = (row.total_time_ms ?? 0) + attempt.duration_ms;
    }
    if (attempt.finished_at && (!row.last_attempt_at || attempt.finished_at > row.last_attempt_at)) {
      row.last_attempt_at = attempt.finished_at;
    }
    grouped.set(attempt.subject_code, row);
  }

  return [...grouped.values()]
    .map(row => ({
      ...row,
      accuracy: row.marks_total > 0 ? row.marks_awarded / row.marks_total : null,
    }))
    .sort((a, b) => b.attempts - a.attempts || a.subject_code.localeCompare(b.subject_code));
}

export function aggregateDailyActivity(attempts: AttemptSummaryView[]): DailyActivityView[] {
  const grouped = new Map<string, DailyActivityView>();
  for (const attempt of attempts) {
    const row = grouped.get(attempt.local_date) ?? {
      user_id: attempt.user_id,
      local_date: attempt.local_date,
      papers: 0,
      total_time_ms: null,
      questions: 0,
      correct: 0,
    };
    row.papers += 1;
    if (attempt.duration_ms !== null) {
      row.total_time_ms = (row.total_time_ms ?? 0) + attempt.duration_ms;
    }
    row.questions += attempt.questions_recorded ?? 0;
    row.correct += attempt.questions_correct ?? 0;
    grouped.set(attempt.local_date, row);
  }
  return [...grouped.values()].sort((a, b) => a.local_date.localeCompare(b.local_date));
}

function attemptLocalHour(attempt: AttemptSummaryView): number | null {
  try {
    const part = new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit',
      hourCycle: 'h23',
      timeZone: attempt.client_timezone,
    }).formatToParts(new Date(attempt.started_at)).find(value => value.type === 'hour');
    const hour = Number(part?.value);
    return Number.isInteger(hour) && hour >= 0 && hour <= 23 ? hour : null;
  } catch {
    // an invalid stored timezone cannot support an honest local-hour
    // claim. Skip it rather than silently treating UTC as the student's time.
    return null;
  }
}

export function aggregateHourOfDay(attempts: AttemptSummaryView[]): HourOfDayView[] {
  const grouped = new Map<number, HourOfDayView>();
  for (const attempt of attempts) {
    const hour = attemptLocalHour(attempt);
    if (hour === null) continue;
    const row = grouped.get(hour) ?? {
      user_id: attempt.user_id,
      local_hour: hour,
      papers: 0,
      total_time_ms: null,
    };
    row.papers += 1;
    if (attempt.duration_ms !== null) {
      row.total_time_ms = (row.total_time_ms ?? 0) + attempt.duration_ms;
    }
    grouped.set(hour, row);
  }
  return [...grouped.values()].sort((a, b) => a.local_hour - b.local_hour);
}

export function calibrationFromFlags(
  flags: QuestionFlagsView[],
  buckets = 10,
): CalibrationPoint[] {
  if (!Number.isInteger(buckets) || buckets < 1) return [];
  const grouped = new Map<number, { confidence: number; correct: number; questions: number }>();
  for (const flag of flags) {
    if (flag.confidence === null || flag.is_correct === null) continue;
    const bucket = Math.min(buckets - 1, Math.max(0, Math.floor(flag.confidence * buckets)));
    const row = grouped.get(bucket) ?? { confidence: 0, correct: 0, questions: 0 };
    row.confidence += flag.confidence;
    row.correct += flag.is_correct ? 1 : 0;
    row.questions += 1;
    grouped.set(bucket, row);
  }

  return [...grouped.entries()].sort(([a], [b]) => a - b).map(([, row]) => {
    const meanConfidence = row.confidence / row.questions;
    const observedAccuracy = row.correct / row.questions;
    return {
      meanConfidence,
      observedAccuracy,
      questions: row.questions,
      gap: observedAccuracy - meanConfidence,
    };
  });
}

export function summariseAnswerChangeRows(
  rows: Array<{ verdict: AnswerChangeVerdict }>,
): AnswerChangeSummary | null {
  if (rows.length === 0) return null;
  const wrongToRight = rows.filter(row => row.verdict === 'wrong_to_right').length;
  const rightToWrong = rows.filter(row => row.verdict === 'right_to_wrong').length;
  const wrongToWrong = rows.filter(row => row.verdict === 'wrong_to_wrong').length;
  return {
    changes: rows.length,
    wrongToRight,
    rightToWrong,
    wrongToWrong,
    netMarks: wrongToRight - rightToWrong,
  };
}
