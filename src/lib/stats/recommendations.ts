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

import { MODEL, Band, type QueueItem } from './model';

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
  /** present only when the input is already scoped to one subject. */
  subjectName?: string;
}): Recommendation {
  const { papers, accuracy, trend, weakest, strongest, subjectName } = input;

  if (papers === 0) {
    return { tone: 'info', finding: 'No completed papers yet.',
             action: 'Sit one and this section fills in.' };
  }
  // Fewer than five papers is not a trend, it is a sample. Saying anything
  // stronger would be reading noise.
  if (papers < MODEL.flags.minPapersForTrend) {
    return { tone: 'info',
             finding: `${papers} paper${papers === 1 ? '' : 's'} so far — too few to read a trend from.`,
             action: 'Around five gives the charts something to say.' };
  }
  if (trend !== null && trend <= -MODEL.flags.notableTrend) {
    return { tone: 'warn',
             finding: `Accuracy is down ${Math.abs(Math.round(trend * 100))} points on your earliest papers.`,
             action: subjectName
               ? `Compare like-for-like ${subjectName} components before treating this as a slide.`
               : 'Check whether the recent papers were harder or a different subject before treating this as a slide.' };
  }
  if (trend !== null && trend >= MODEL.flags.notableTrend) {
    return { tone: 'good',
             finding: `Accuracy is up ${Math.round(trend * 100)} points since you started.`,
             action: subjectName
               ? `${subjectName} is improving; use the component chart to see which paper is driving it.`
               : weakest ? `${weakest.name} is still your lowest at ${pct(weakest.accuracy)} — the most marks are there.` : undefined };
  }
  if (weakest && strongest && strongest.accuracy - weakest.accuracy >= MODEL.flags.subjectSpread) {
    return { tone: 'info',
             finding: `${weakest.name} (${pct(weakest.accuracy)}) trails ${strongest.name} (${pct(strongest.accuracy)}).`,
             action: 'A subject gap that wide is usually content, not technique.' };
  }
  return { tone: 'info',
           finding: `Holding steady at ${accuracy !== null ? pct(accuracy) : '—'} across ${papers} papers${subjectName ? ` in ${subjectName}` : ''}.`,
           action: subjectName
             ? 'Use the paper score sequence and component trend to find the next repeatable gain.'
             : weakest ? `${weakest.name} at ${pct(weakest.accuracy)} is where the marks are.` : undefined };
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
  if (daysSinceLast !== null && daysSinceLast >= MODEL.flags.veryStaleDays) {
    return { tone: 'warn',
             finding: `${daysSinceLast} days since your last paper.`,
             action: 'Recall decays fastest in the first fortnight — a short paper now is worth more than a long one next week.' };
  }
  if (daysSinceLast !== null && daysSinceLast >= MODEL.flags.staleDays) {
    return { tone: 'warn', finding: `${daysSinceLast} days since your last paper.`,
             action: 'Your streak is broken; the cheapest fix is one paper today.' };
  }
  if (currentStreak >= MODEL.flags.goodStreakDays) {
    return { tone: 'good', finding: `${currentStreak}-day streak.`,
             action: currentStreak >= longestStreak ? 'Your best run so far.' : `Your best is ${longestStreak}.` };
  }
  if (longestStreak >= MODEL.flags.establishedStreakDays && currentStreak <= 1) {
    return { tone: 'info',
             finding: `You have held a ${longestStreak}-day streak before; you are on ${currentStreak} now.`,
             action: 'Consistency moved your accuracy more than session length did.' };
  }
  return { tone: 'info', finding: `${papers} papers, ${currentStreak}-day streak.`,
           action: 'Regular short sessions beat occasional long ones.' };
}

// ------------------------------------------------------------ next steps
/**
 * The headline action, from the top of the revision queue.
 *
 * Says the thing rather than describing the chart. The queue below the banner
 * already carries the ranking; this states the one move worth making, and
 * names the number behind it so it can be checked.
 */
export function queueRecommendation(input: {
  queue: QueueItem[];
  missed: number;
}): Recommendation {
  const top = input.queue[0];
  if (!top) {
    return { tone: 'info', finding: 'Nothing to recommend yet.',
             action: 'Sit a paper on a topic-tagged syllabus and this fills in.' };
  }

  const r = top.reading;
  const acc = r.accuracy.point;

  // A topic we cannot separate from guessing needs teaching, not drilling.
  // Sending a student to practise it is the ROPL failure mode - see model.ts.
  if (r.band === Band.Struggling) {
    return { tone: 'warn',
             finding: `${top.topicName} is not yet clear of guessing — ${pct(acc)} across ${r.questions} questions.`,
             action: 'Read the topic up before practising it. More questions on something you have not learned yet mostly generate more wrong answers.' };
  }
  if (r.band === Band.Untested) {
    return { tone: 'info',
             finding: `${top.topicName} has only ${r.questions} question${r.questions === 1 ? '' : 's'} behind it.`,
             action: 'Not a weakness — a blind spot. Sit a paper covering it before deciding anything.' };
  }
  if (top.driver === 'decay' && r.daysSincePractice !== null) {
    return { tone: 'info',
             finding: `${top.topicName} was last practised ${r.daysSincePractice} days ago and is fading.`,
             action: 'You knew this. A short revisit now costs less than relearning it later.' };
  }
  return { tone: 'info',
           finding: `${top.topicName} is where the next marks are — ${pct(acc)} across ${r.questions} questions.`,
           action: input.missed > 0
             ? `Start with the ${input.missed} question${input.missed === 1 ? '' : 's'} you have already got wrong.`
             : 'Practise it before anything you are already good at.' };
}

// ----------------------------------------------------------------- topics
/**
 * moved into model.ts. Every threshold in this file now comes from there -
 * a recommendation is a claim about the student, and the number behind the
 * claim belongs with the rest of the model rather than beside the sentence it
 * happens to produce. Re-exported so existing callers keep working.
 */
export const TOPIC_MIN_QUESTIONS = MODEL.queue.minQuestions;

export interface TopicReading {
  name: string;
  questions: number;
  accuracy: number | null;
}

export function topicRecommendation(input: { topics: TopicReading[] }): Recommendation {
  const { topics } = input;

  if (topics.length === 0) {
    return { tone: 'info', finding: 'No topic-tagged questions yet.',
             action: 'Topic tagging covers the multiple-choice syllabuses; sit one and this section fills in.' };
  }

  // Only topics with enough behind them get named. The rest still appear in
  // the chart, where their question count is visible beside them.
  const solid = topics
    .filter((t): t is TopicReading & { accuracy: number } =>
      t.accuracy !== null && t.questions >= TOPIC_MIN_QUESTIONS)
    .sort((a, b) => a.accuracy - b.accuracy);

  if (solid.length === 0) {
    return { tone: 'info',
             finding: `${topics.length} topic${topics.length === 1 ? '' : 's'} seen, none with ${TOPIC_MIN_QUESTIONS} questions behind it yet.`,
             action: 'A topic needs a handful of questions before its accuracy means anything.' };
  }

  const weakest = solid[0]!;
  const strongest = solid[solid.length - 1]!;

  if (weakest.accuracy < MODEL.flags.contentGapBelow) {
    return { tone: 'warn',
             finding: `${weakest.name} is at ${pct(weakest.accuracy)} across ${weakest.questions} questions.`,
             action: 'Below half is a content gap rather than a technique one — revise it before sitting another paper on it.' };
  }
  if (solid.length >= MODEL.flags.minTopicsForSpread
      && strongest.accuracy - weakest.accuracy >= MODEL.flags.notableSpread) {
    return { tone: 'info',
             finding: `${weakest.name} (${pct(weakest.accuracy)}) trails ${strongest.name} (${pct(strongest.accuracy)}).`,
             action: `A ${Math.round((strongest.accuracy - weakest.accuracy) * 100)}-point spread inside one subject is where the cheapest marks are.` };
  }
  return { tone: 'good',
           finding: `Evenly spread across ${solid.length} topics, weakest ${weakest.name} at ${pct(weakest.accuracy)}.`,
           action: 'No single topic is dragging you down; breadth is not the problem.' };
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
  if (overRate >= MODEL.flags.overconfidentRate) {
    return { tone: 'warn',
             finding: `${pct(overRate)} of questions were confident and wrong (${overconfident} of ${questions}).`,
             action: 'These are misconceptions, not slips — review the ones you were surest about first.' };
  }
  if (guessRate >= MODEL.flags.guessRate) {
    return { tone: 'warn',
             finding: `${pct(guessRate)} of questions look like guesses${guessAccuracy !== null ? `, landing ${pct(guessAccuracy)} of the time` : ''}.`,
             action: 'Eliminating even one option before answering roughly doubles a guess. Slow down rather than skipping.' };
  }
  if (underRate >= MODEL.flags.underconfidentRate) {
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
