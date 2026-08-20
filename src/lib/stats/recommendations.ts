// ==========================================================================
//
// Section recommendations: rules, not a language model.
//
// WHY RULES. A recommendation banner sits directly beside the chart it
// describes. A model that says "your accuracy is improving" next to a flat line
// destroys confidence in the whole page, and that failure is silent - nobody
// reports it, they just stop trusting the numbers. A rule cannot contradict the
// data because it is computed from it.
//
// Three other properties matter here:
//   - Deterministic. The same data gives the same advice, so a change in the
//     banner means the student's behaviour changed, not that the model's
//     sampling did. This page is meant to be compared with itself over time.
//   - Auditable. Every threshold below is visible and arguable. The confidence
//     and guess cut-offs elsewhere in this app were PICKED, NOT MEASURED
//     (docs/roadmap.md B6), and anything built on them inherits that. A rule
//     lets you see the number and change it; a model buries it.
//   - Free and instant. No key, no round trip, no failure mode on the render
//     path of a page that already makes seven queries.
//
// WHERE A MODEL WOULD EARN ITS PLACE: synthesising ACROSS sections into a study
// plan ("your Chemistry accuracy is fine but you are guessing on it, and your
// guesses are 30% - do untimed sets"), which is a genuinely generative task
// over already-computed facts. That is a different feature from a per-section
// banner, and it should quote the numbers it was given rather than invent them.
//
// EVERY RULE RETURNS A NUMBER IT USED. A recommendation that cannot show its
// working is indistinguishable from a guess.
// ==========================================================================

export type Tone = 'good' | 'warn' | 'info';

export interface Recommendation {
  tone: Tone;
  /** The finding, stated as fact and carrying the number behind it. */
  finding: string;
  /** What to do about it. Omitted when the finding is simply good news. */
  action?: string;
}

const pct = (n: number) => `${Math.round(n * 100)}%`;

// --------------------------------------------------------------- progress
export function progressRecommendation(input: {
  papers: number;
  accuracy: number | null;
  /** Change in accuracy, latest vs earliest, as a ratio. Null if too few. */
  trend: number | null;
  weakest: { name: string; accuracy: number } | null;
  strongest: { name: string; accuracy: number } | null;
}): Recommendation {
  const { papers, accuracy, trend, weakest, strongest } = input;

  if (papers === 0) {
    return { tone: 'info', finding: 'No completed papers yet.',
             action: 'Sit one and this section fills in.' };
  }
  // Fewer than five papers is not a trend, it is a sample. Saying anything
  // stronger would be reading noise.
  if (papers < 5) {
    return { tone: 'info',
             finding: `${papers} paper${papers === 1 ? '' : 's'} so far — too few to read a trend from.`,
             action: 'Around five gives the charts something to say.' };
  }
  if (trend !== null && trend <= -0.05) {
    return { tone: 'warn',
             finding: `Accuracy is down ${Math.abs(Math.round(trend * 100))} points on your earliest papers.`,
             action: 'Check whether the recent papers were harder or a different subject before treating this as a slide.' };
  }
  if (trend !== null && trend >= 0.05) {
    return { tone: 'good',
             finding: `Accuracy is up ${Math.round(trend * 100)} points since you started.`,
             action: weakest ? `${weakest.name} is still your lowest at ${pct(weakest.accuracy)} — the most marks are there.` : undefined };
  }
  if (weakest && strongest && strongest.accuracy - weakest.accuracy >= 0.15) {
    return { tone: 'info',
             finding: `${weakest.name} (${pct(weakest.accuracy)}) trails ${strongest.name} (${pct(strongest.accuracy)}).`,
             action: 'A subject gap that wide is usually content, not technique.' };
  }
  return { tone: 'info',
           finding: `Holding steady at ${accuracy !== null ? pct(accuracy) : '—'} across ${papers} papers.`,
           action: weakest ? `${weakest.name} at ${pct(weakest.accuracy)} is where the marks are.` : undefined };
}

// ------------------------------------------------------------- engagement
export function engagementRecommendation(input: {
  papers: number;
  currentStreak: number;
  longestStreak: number;
  daysSinceLast: number | null;
  avgPaperMs: number | null;
}): Recommendation {
  const { papers, currentStreak, longestStreak, daysSinceLast } = input;

  if (papers === 0) {
    return { tone: 'info', finding: 'No sessions recorded yet.' };
  }
  if (daysSinceLast !== null && daysSinceLast >= 14) {
    return { tone: 'warn',
             finding: `${daysSinceLast} days since your last paper.`,
             action: 'Recall decays fastest in the first fortnight — a short paper now is worth more than a long one next week.' };
  }
  if (daysSinceLast !== null && daysSinceLast >= 7) {
    return { tone: 'warn', finding: `${daysSinceLast} days since your last paper.`,
             action: 'Your streak is broken; the cheapest fix is one paper today.' };
  }
  if (currentStreak >= 7) {
    return { tone: 'good', finding: `${currentStreak}-day streak.`,
             action: currentStreak >= longestStreak ? 'Your best run so far.' : `Your best is ${longestStreak}.` };
  }
  if (longestStreak >= 5 && currentStreak <= 1) {
    return { tone: 'info',
             finding: `You have held a ${longestStreak}-day streak before; you are on ${currentStreak} now.`,
             action: 'Consistency moved your accuracy more than session length did.' };
  }
  return { tone: 'info', finding: `${papers} papers, ${currentStreak}-day streak.`,
           action: 'Regular short sessions beat occasional long ones.' };
}

// ------------------------------------------------------------------ focus
export function focusRecommendation(input: {
  questions: number;
  overconfident: number;
  underconfident: number;
  guesses: number;
  guessAccuracy: number | null;
  answerChanges: { wrongToRight: number; rightToWrong: number; netMarks: number } | null;
}): Recommendation {
  const { questions, overconfident, underconfident, guesses, guessAccuracy, answerChanges } = input;

  if (questions === 0) {
    return { tone: 'info', finding: 'No questions recorded yet.' };
  }

  const overRate = overconfident / questions;
  const underRate = underconfident / questions;
  const guessRate = guesses / questions;

  // Answer changing is checked first when it is actively costing marks,
  // because it is the most directly actionable habit on this page.
  if (answerChanges && answerChanges.netMarks < 0) {
    return { tone: 'warn',
             finding: `Changing your answer has cost you ${Math.abs(answerChanges.netMarks)} marks net — ${answerChanges.rightToWrong} right-to-wrong against ${answerChanges.wrongToRight} wrong-to-right.`,
             action: 'Your first instinct is beating your second. Only change with a concrete reason, not a feeling.' };
  }
  if (overRate >= 0.1) {
    return { tone: 'warn',
             finding: `${pct(overRate)} of questions were confident and wrong (${overconfident} of ${questions}).`,
             action: 'These are misconceptions, not slips — review the ones you were surest about first.' };
  }
  if (guessRate >= 0.15) {
    return { tone: 'warn',
             finding: `${pct(guessRate)} of questions look like guesses${guessAccuracy !== null ? `, landing ${pct(guessAccuracy)} of the time` : ''}.`,
             action: 'Eliminating even one option before answering roughly doubles a guess. Slow down rather than skipping.' };
  }
  if (underRate >= 0.15) {
    return { tone: 'info',
             finding: `${pct(underRate)} of questions were right but hesitant (${underconfident} of ${questions}).`,
             action: 'You know more than you are backing. Second-guessing is costing you time, not marks.' };
  }
  if (answerChanges && answerChanges.netMarks > 0) {
    return { tone: 'good',
             finding: `Changing your answer has won you ${answerChanges.netMarks} marks net.`,
             action: 'Reviewing is paying — keep leaving time for a second pass.' };
  }
  return { tone: 'good', finding: `No dominant weakness across ${questions} questions.`,
           action: 'Calibration and timing both look reasonable.' };
}
