// ==========================================================================
//
// THE METRIC MODEL. Every statistical assumption this app makes lives here.
//
// THE RULE
// No other file computes a metric, picks a threshold, or weights a sum. Views
// aggregate, components render, queries fetch - and all three call into this
// file for anything that constitutes a claim about the student. If you find
// yourself writing `if (accuracy < 0.5)` anywhere else, the constant belongs
// here and the comparison belongs in a function exported from here.
//
// WHY. Two reasons, and the second is the real one.
//   1. These numbers are arguable. A threshold buried in a Vue template cannot
//      be found, reviewed, or changed with confidence, and nobody can tell
//      whether the 0.5 in one component means the same thing as the 0.5 in
//      another.
//   2. Most of this is INFERENCE, not measurement. "You have mastered waves"
//      is a claim with a model behind it and error bars around it. Scattering
//      that model across a page makes it look like arithmetic. Keeping it in
//      one file, with the citation next to each constant, keeps it honest -
//      and makes it obvious how much of this page is estimate rather than fact.
//
// EVERY CONSTANT IS EITHER CITED OR MARKED PICKED. `MODEL` below is the whole
// tunable surface. Anything in it tagged PICKED has no empirical backing in
// our data and is a starting value to be replaced once we have usage data;
// anything with a citation is taken from the literature named.
//
// See docs/solver/stats_priority.md for why these five metrics and not others.
// ==========================================================================

// the only import in this file, and it is DATA rather than behaviour -
// Cambridge's published grade thresholds, scraped and averaged by
// scripts/gt/build.py. Everything else here is self-contained on purpose: the
// model should be readable, and testable, without pulling the app in with it.
//
// RELATIVE, not the '@/' alias the rest of src/ uses. `npm test` runs these
// modules through node --experimental-strip-types, which resolves neither
// tsconfig paths nor Vite aliases - an aliased import here would compile fine
// and break the test run, which is the wrong way round for the one file in
// this app whose correctness is hardest to eyeball.
import {
  PAPER_THRESHOLDS, SESSION_THRESHOLDS, SEASON_NAMES,
  type PaperThresholds,
} from '../../constants/gradeThresholds.ts';

// --------------------------------------------------------------------------
// Tunable surface. One object, so the whole model can be read in one screen
// and diffed in one place.
// --------------------------------------------------------------------------
export const MODEL = {
  /** SS A - binomial inference. */
  interval: {
    /**
     * Two-sided 95% normal quantile, for the Wilson score interval.
     * Wilson, E.B. (1927), JASA 22(158), 209-212.
     */
    z95: 1.959964,
  },

  /** SS B - recency-weighted mastery. See the SS B header for what this replaced. */
  mastery: {
    /**
     * Half-life of the recency weighting, in QUESTIONS (not days - decay in
     * time is SS C and is a separate term). A question this many answers ago
     * counts half as much as the latest one.
     *
     * PICKED at 20, roughly half a paper's worth of questions on one topic:
     * long enough that a single unlucky question cannot swing the estimate,
     * short enough that a topic revised last month does not sit on evidence
     * from before it was revised.
     */
    recencyHalfLifeQuestions: 20,
    /**
     * The bar for "mastered", when we have no real threshold for the paper.
     *
     * NORMALLY UNUSED. masteryBar() below reads the actual published grade
     * threshold for the paper in question - see SS F - and only falls back to
     * this for a paper the scrape found nothing for.
     *
     * Note what the band test does with it: it requires the LOWER bound of the
     * accuracy interval to clear the bar, so mastery has to be demonstrated
     * rather than merely observed once.
     */
    fallbackMasteredAbove: 0.70,
  },

  /** SS C - forgetting. Ebbinghaus (1885); Settles & Meeder (2016). */
  decay: {
    /**
     * Half-life model ĥ = 2^(θ·x), Settles & Meeder (2016) eq. 2, with
     * x = (1, sqrt(correct), sqrt(incorrect)).
     *
     * θ IS HAND-PICKED, NOT TRAINED. The paper fits θ to 13M learning traces;
     * we have one user. The paper anticipates this - SS3.3 notes that Pimsleur
     * and Leitner "can be interpreted as special cases of (2) using a few
     * fixed, hand-picked weights" - so a fixed θ is a documented degenerate
     * case of the model rather than a departure from it. Replace with a fit
     * once there are traces to fit to.
     */
    theta0: 1.0,      // bias: a topic with no history has a ~2 day half-life
    thetaCorrect: 1.0,   // each sqrt(correct recall) roughly doubles it
    thetaIncorrect: -0.5, // each sqrt(failure) roughly halves it
    /** Half-life is clamped to this range, in days. PICKED, for sanity. */
    minHalfLifeDays: 1,
    maxHalfLifeDays: 365,
  },

  // SS D needs no constants of its own: the region of proximal learning is
  // bounded below by chance (1/optionCount, structural) and above by
  // the paper's published top-grade threshold, and peaks halfway between.

  /** SS E - revision queue ranking. */
  queue: {
    /**
     * Weights of the three drives. Sum to 1 so the score stays in [0,1] and
     * a percentage is meaningful. ALL PICKED - there is no ground truth for
     * "should have revised this" to fit against, and there will not be until
     * we can measure whether a recommended topic improved afterwards.
     */
    wGap: 0.50,    // how learnable is this right now (ROPL)
    wDecay: 0.30,  // how much has faded (spacing)
    wMarks: 0.20,  // how many marks ride on it
    /**
     * A topic needs this many answered questions before the queue will name
     * it on the strength of its accuracy alone. Below it, the topic can still
     * appear - as UNTESTED, which is a different and honest recommendation.
     * PICKED: under eight questions one unlucky guess moves accuracy by more
     * than 12 points, which is wider than the gaps being ranked.
     */
    minQuestions: 8,
    /** How many items the queue shows. Presentation, but capped centrally. */
    size: 6,
  },

  /** SS F - grade estimation. */
  grade: {
    /**
     * Confidence level for the reported grade RANGE, as a z-quantile.
     * Narrower than 95% deliberately: a 95% band over 40 questions spans most
     * of the grade scale and communicates nothing. 80% two-sided.
     */
    z: 1.281552,
    /** Minimum answered questions before any grade is shown at all. PICKED. */
    minQuestions: 40,
  },

  /** SS G - behavioural flags. Migrated here from recommendations.ts. */
  flags: {
    /** Accuracy below which a topic is called a content gap. PICKED. */
    contentGapBelow: 0.50,
    /**
     * Grade a pooled result must fall BELOW before we suggest more practice
     * on a subject. PICKED, as the standard pass most candidates are aiming
     * at - so the nudge means "you are short of the grade you want" rather
     * than "you are short of some number we invented".
     */
    practiceBelowGrade: 'C',
    /** Papers needed before an average across them means anything. PICKED. */
    minPapersForSubject: 2,
    /** Spread across topics that makes the gap worth naming. PICKED. */
    notableSpread: 0.25,
    /** Spread across SUBJECTS that makes the gap worth naming. PICKED, and
     *  lower than the topic figure because subjects are coarser: a 15-point
     *  gap between two whole subjects is already a lot of marks. */
    subjectSpread: 0.15,
    /** Topics needed before a spread is worth reporting at all. PICKED. */
    minTopicsForSpread: 3,
    /** Consecutive days that count as a strong streak. PICKED. */
    goodStreakDays: 7,
    /** A past streak long enough to hold up as evidence of capability. PICKED. */
    establishedStreakDays: 5,
    /** Overall accuracy trend that counts as movement, in ratio. PICKED. */
    notableTrend: 0.05,
    // the three DETECTION thresholds, moved out of v_question_flags by
    // migration 00000000000007. They decided in SQL what counts as a guess or
    // as overconfidence, which made them the only claims about a student that
    // did not live in this file - so checking one meant writing a migration
    // and comparing two settings was impossible. All three are PICKED and
    // docs/roadmap.md B6 asks for them to be measured; that is now a one-line
    // edit here. Distinct from the *Rate flags below, which decide when a
    // banner is worth writing, not what an individual question is.
    /** Confidence at or above which a WRONG answer is overconfident. PICKED. */
    overconfidentAbove: 0.70,
    /** Confidence at or below which a RIGHT answer is underconfident. PICKED. */
    underconfidentBelow: 0.40,
    /** Fraction of the paper's median time under which an answer looks rushed. PICKED. */
    guessTimeRatio: 0.40,
    /** Interaction depth at or below which there was essentially no working. PICKED. */
    guessExplorationMax: 1,

    /** Share of questions that were confident-and-wrong. PICKED. */
    overconfidentRate: 0.10,
    /** Share of questions that look like guesses. PICKED. */
    guessRate: 0.15,
    /** Share of questions that were right-but-hesitant. PICKED. */
    underconfidentRate: 0.15,
    /** Papers below which no trend is claimed. PICKED. */
    minPapersForTrend: 5,
    /**
     * Papers at each end of the history that the accuracy trend compares.
     * PICKED, and paired with minPapersForTrend: five papers is enough for a
     * mean to mean something and few enough that a student who has sat a
     * dozen still gets a reading.
     */
    trendWindowPapers: 5,
    /**
     * Length of the "recently" window on the dashboard, in days. PICKED as a
     * week because study happens on a weekly timetable - a 5- or 10-day
     * window would straddle weekends unevenly and make the comparison move
     * for reasons that are about the calendar rather than the student.
     */
    recentWindowDays: 7,
    /** Days of silence that earn a warning. PICKED. */
    staleDays: 7,
    veryStaleDays: 14,
  },
} as const;

// --------------------------------------------------------------------------
// SS A. Binomial inference
//
// Every accuracy on this page is a proportion from a small sample, and the
// naive ratio is the wrong statistic to RANK by: it makes the best and worst
// items the ones with least evidence. Wilson (1927) inverts the score test
// instead of assuming normality around p-hat, which keeps the bounds inside
// [0,1] and holds its coverage at small n and at extreme proportions - exactly
// our case, since a topic can easily be 5-for-5.
// --------------------------------------------------------------------------

export interface Interval {
  /** Point estimate, uncorrected. successes / trials. */
  point: number;
  /** Wilson centre - the estimate shrunk toward 1/2 by the evidence. */
  centre: number;
  lower: number;
  upper: number;
  /** upper - lower. How much we do not know. */
  width: number;
}

/**
 * Wilson score interval for a binomial proportion.
 *
 *   centre = (p + z^2/2n) / (1 + z^2/n)
 *   half   = z * sqrt( p(1-p)/n + z^2/4n^2 ) / (1 + z^2/n)
 *
 * Wilson, E.B. (1927). "Probable Inference, the Law of Succession, and
 * Statistical Inference." JASA 22(158), 209-212.
 */
// `z: number` is annotated rather than inferred: MODEL is `as const`, so the
// default would narrow the parameter to the literal 1.959964 and refuse the
// 80% quantile the grade estimate passes in.
export function wilson(successes: number, trials: number, z: number = MODEL.interval.z95): Interval {
  if (trials <= 0) return { point: 0, centre: 0.5, lower: 0, upper: 1, width: 1 };
  const p = successes / trials;
  const z2 = z * z;
  const denom = 1 + z2 / trials;
  const centre = (p + z2 / (2 * trials)) / denom;
  const half = (z * Math.sqrt((p * (1 - p)) / trials + z2 / (4 * trials * trials))) / denom;
  const lower = Math.max(0, centre - half);
  const upper = Math.min(1, centre + half);
  return { point: p, centre, lower, upper, width: upper - lower };
}

// --------------------------------------------------------------------------
// SS B. Mastery - recency-weighted accuracy
//
// WHAT THIS REPLACED, AND WHY. This section was Bayesian Knowledge Tracing
// (Corbett & Anderson 1995) - the standard choice, and the one the design note
// called for. It was implemented, tested, and then run against real practice
// data, where it put 43 of 51 topics in "mastered" at accuracies between 61%
// and 73%. A banding that calls 84% of topics mastered at 70% accuracy is
// useless whatever its pedigree.
//
// The cause is GRAIN, and it is worth stating because it will come up again.
// BKT models one SKILL, in one of two states, where a wrong answer from a
// knowing student is a slip - a rare event. Baker, Corbett & Aleven (2008)
// show the model becomes unidentifiable unless slip is capped near 0.10.
// A Cambridge syllabus TOPIC is not one skill; "Thermal effects" is dozens.
// Measured on our own data the median topic error rate is 0.30 - three times
// the ceiling - and 48 of 49 topics with enough evidence exceed it. A student
// at 70% on a topic is not slipping on a thing they know; they know roughly
// 70% of the thing. BKT has no way to represent that, so it reports certainty.
//
// BKT would be the right model at QUESTION-SKILL grain. We do not have skills,
// we have topics, and pretending otherwise would put a confident wrong number
// in front of a student.
//
// What survives is the property that motivated reaching for BKT in the first
// place: ORDER MATTERS. Eight-out-of-ten is a student who has just got it if
// the misses came first, and one who is losing it if they came last, and a
// plain ratio cannot tell them apart. Exponential recency weighting keeps that
// while making no claim about hidden states:
//
//   m = sum_i w_i x_i / sum_i w_i,     w_i = 2^(-(n-i)/lambda)
//
// where x_i is 1 for a correct answer, n is the most recent question, and
// lambda is a half-life in questions. The 2^(-x) form is deliberately the same
// one as the forgetting curve in SS C - one decay shape in the model, not two.
//
// Decayed-exposure weighting of this kind is the standard treatment in the
// knowledge-tracing literature that followed BKT; see Performance Factors
// Analysis (Pavlik, Cen & Koedinger 2009), which replaces BKT's latent state
// with weighted counts of prior successes and failures for closely related
// reasons.
//
// The result is directly interpretable and directly checkable: it estimates
// the probability the student gets the NEXT question on this topic right.
// --------------------------------------------------------------------------

export interface Trial {
  isCorrect: boolean;
  /** Options on the question. Sets chance level at 1/optionCount. */
  optionCount: number;
}

/**
 * Recency-weighted proportion correct.
 *
 * `trials` MUST be in chronological order, oldest first. Out-of-order input
 * does not throw; it silently returns a different number, which is the worst
 * failure mode available, so callers sort and this comment exists.
 *
 * Returns null for an empty sequence rather than a number - "no evidence" is
 * not a mastery of zero, and every caller has to handle the difference.
 */
export function recencyWeightedAccuracy(trials: Trial[]): number | null {
  if (trials.length === 0) return null;
  const lambda = MODEL.mastery.recencyHalfLifeQuestions;
  const n = trials.length - 1;
  let num = 0;
  let den = 0;
  for (let i = 0; i < trials.length; i++) {
    const w = 2 ** (-(n - i) / lambda);
    den += w;
    if (trials[i]!.isCorrect) num += w;
  }
  return num / den;
}

/** Chance level on a k-option question. Structural, not fitted. */
export function chanceLevel(optionCount: number): number {
  return 1 / Math.max(2, optionCount);
}

// --------------------------------------------------------------------------
// SS C. Retention - the forgetting curve
//
// Ebbinghaus, H. (1885). Über das Gedächtnis.
// Settles, B. & Meeder, B. (2016). "A Trainable Spaced Repetition Model for
// Language Learning." ACL 2016, 1848-1858.
//
// Settles & Meeder eq. 1:   p = 2^(-Δ/h)
//   Δ = lag since last practice, h = half-life. At Δ = h, p = 0.5 - the point
//   the paper describes as "on the verge of being unable to remember".
//
// Settles & Meeder eq. 2:   ĥ = 2^(θ·x)
//   Half-life grows exponentially with successful exposure. See MODEL.decay
//   for why θ here is fixed rather than fitted, and why that is a documented
//   special case of the paper's own model rather than a shortcut.
// --------------------------------------------------------------------------

/** ĥ = 2^(θ0 + θ+ sqrt(correct) + θ- sqrt(incorrect)), clamped. Days. */
export function halfLifeDays(correct: number, incorrect: number): number {
  const { theta0, thetaCorrect, thetaIncorrect, minHalfLifeDays, maxHalfLifeDays } = MODEL.decay;
  const exponent = theta0
    + thetaCorrect * Math.sqrt(Math.max(0, correct))
    + thetaIncorrect * Math.sqrt(Math.max(0, incorrect));
  return Math.min(maxHalfLifeDays, Math.max(minHalfLifeDays, 2 ** exponent));
}

/**
 * p = 2^(-Δ/h). Probability the topic is still retrievable today.
 * Returns 1 for a topic practised today, whatever its history.
 */
export function retention(daysSinceLastPractice: number, correct: number, incorrect: number): number {
  const h = halfLifeDays(correct, incorrect);
  return 2 ** (-Math.max(0, daysSinceLastPractice) / h);
}

/**
 * Past its own half-life.
 *
 * NOT a picked threshold - 0.5 is what "half-life" means. Settles & Meeder
 * describe this exact point as the student being "on the verge of being unable
 * to remember", which is the moment a spaced-repetition system exists to catch.
 */
export function isFading(retention: number): boolean {
  return retention < 0.5;
}

/** Whole local days between two YYYY-MM-DD dates. */
export function daysBetween(fromIso: string, toIso: string): number {
  const a = Date.parse(`${fromIso}T00:00:00Z`);
  const b = Date.parse(`${toIso}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(b)) return 0;
  return Math.max(0, Math.round((b - a) / 86_400_000));
}

// --------------------------------------------------------------------------
// SS D. Banding - the region of proximal learning
//
// Metcalfe, J. & Kornell, N. (2005). "A Region of Proximal Learning model of
// study time allocation." Journal of Memory and Language 52(4), 463-477.
//
// Effective learners drop what is already mastered, then work the MODERATELY
// difficult material - not the hardest. Time spent on items far beyond reach
// is close to wasted; time on mastered items entirely so.
//
// This is why the split is three ways and not two. An easy/hard cut sends the
// student at their single worst topic, which is frequently the one practice
// cannot fix, and is the worst available use of their remaining time.
//
// BOTH EDGES OF THE PROXIMAL REGION ARE DERIVED, NOT PICKED:
//   lower edge = chance, 1/optionCount. Below it there is no evidence the
//                student knows anything, so practice is not the intervention.
//   upper edge = the paper's REAL top-grade threshold, from Cambridge's own
//                published tables (SS F). Above it the topic is not where the
//                next mark comes from.
// The peak sits halfway between. On IGCSE Physics Paper 2, whose published
// grade A averages ~62%, that is 25% .. 62%, peaking at ~44% - materially
// different from the 80% bar this model used before the real thresholds were
// scraped, and the reason nothing ever reached "mastered" under the old one.
// --------------------------------------------------------------------------

export const Band = {
  /** Confidently at grade-A standard. Stop practising this. */
  Mastered: 'mastered',
  /** The region of proximal learning. Cheapest marks are here. */
  Proximal: 'proximal',
  /** Enough evidence, and it says you are not reliably above chance. */
  Struggling: 'struggling',
  /** Not enough evidence to say anything. Not the same as being bad at it. */
  Untested: 'untested',
} as const;
export type Band = typeof Band[keyof typeof Band];

export interface TopicReading {
  /** Recency-weighted accuracy. Null when there is no evidence at all. */
  mastery: number | null;
  accuracy: Interval;
  questions: number;
  optionCount: number;
  band: Band;
  /** This paper's real top-grade threshold, the upper edge of proximal. */
  bar: number;
  retention: number;
  daysSincePractice: number | null;
  /** Carried so callers never have to re-derive them from the rows. */
  marksAwarded: number;
  marksTotal: number;
}

/**
 * Bands a topic from its accuracy interval.
 *
 * Both tests use a BOUND of the interval rather than the point estimate, and
 * that is the whole idea: a claim about a student should have to survive the
 * uncertainty in the evidence behind it.
 *
 *   Mastered   - the LOWER bound clears the grade-A bar. Being at 85% on six
 *                questions does not qualify; the interval is too wide.
 *   Struggling - the LOWER bound is at or below chance, i.e. we cannot
 *                distinguish this student from someone guessing. That is a
 *                statistical statement, not a picked cut-off, and it is the
 *                difference between "weak here" and "no evidence of knowing
 *                this at all" - which want different advice: practice for the
 *                first, teaching for the second.
 */
export function bandOf(
  accuracy: Interval,
  questions: number,
  optionCount: number,
  /** The paper's real top-grade threshold. See masteryBar() in SS F. */
  bar: number,
): Band {
  if (questions < MODEL.queue.minQuestions) return Band.Untested;
  if (accuracy.lower >= bar) return Band.Mastered;
  if (accuracy.lower <= chanceLevel(optionCount)) return Band.Struggling;
  return Band.Proximal;
}

/**
 * Triangular kernel over mastery, peaking in the middle of the proximal region
 * and falling to zero at both of its edges. The ROPL claim - "study the
 * middle" - as a number.
 *
 * A topic with no evidence returns the peak: an untouched topic is exactly the
 * thing a revision queue should raise, and scoring it zero would bury it.
 */
export function proximity(mastery: number | null, optionCount: number, bar: number): number {
  const lo = chanceLevel(optionCount);
  const hi = bar;
  if (mastery === null) return 1;
  const peak = (lo + hi) / 2;
  const width = (hi - lo) / 2;
  if (width <= 0) return 0;
  return Math.max(0, 1 - Math.abs(mastery - peak) / width);
}

// --------------------------------------------------------------------------
// SS E. The revision queue
//
// A weighted sum of three drives, each already in [0,1], with weights summing
// to 1 so the result reads as a percentage.
//
// WHY A SUM AND NOT A PRODUCT. A product would zero a mastered topic however
// stale it had become, and that is wrong: Metcalfe's "drop what is mastered"
// governs where NEW learning time goes, while Ebbinghaus governs MAINTENANCE,
// and the two are different claims. A sum lets a mastered-but-faded topic
// resurface on the decay term alone, which is the behaviour spaced repetition
// exists to produce.
//
// The three terms are returned alongside the score so the UI can say WHY an
// item is in the queue. Jivet et al. (2020) found "transparency of design" one
// of three constructs that determine whether students act on a dashboard at
// all; an unexplained ranking is one students are entitled to ignore.
// --------------------------------------------------------------------------

export interface QueueInput {
  topicId: string;
  topicName: string;
  subjectCode: string;
  reading: TopicReading;
  /** Marks this topic carries, over the largest any topic carries. 0..1. */
  marksShare: number;
}

export interface QueueItem extends QueueInput {
  score: number;
  /** The three components, for explaining the ranking. */
  terms: { gap: number; decay: number; marks: number };
  /** Which term contributed most. Drives the one-word reason in the UI. */
  driver: 'gap' | 'decay' | 'marks';
}

export function revisionPriority(input: QueueInput): QueueItem {
  const { wGap, wDecay, wMarks } = MODEL.queue;
  const gap = proximity(input.reading.mastery, input.reading.optionCount, input.reading.bar);
  const decay = 1 - input.reading.retention;
  const marks = Math.min(1, Math.max(0, input.marksShare));

  const terms = { gap: wGap * gap, decay: wDecay * decay, marks: wMarks * marks };
  const score = terms.gap + terms.decay + terms.marks;
  const driver = (Object.entries(terms).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'gap') as
    'gap' | 'decay' | 'marks';

  return { ...input, score, terms, driver };
}

// --------------------------------------------------------------------------
// SS F. Grade estimation
//
// WHAT THIS IS NOT: a predicted qualification grade. It is a grade on ONE
// COMPONENT - the multiple-choice paper - which for most of these syllabuses
// is one of two or three that combine into the final grade. Anyone reading it
// as "my IGCSE grade" is being misled, so the UI carries the component caveat
// wherever the letter goes.
//
// THE THRESHOLDS ARE REAL. src/constants/gradeThresholds.ts is generated by
// scripts/gt/build.py from Cambridge's own published grade-threshold documents.
// It replaced a table of "typical" percentages (A at 80%, C at 60%) which the
// first real document showed to be badly wrong: IGCSE Physics Extended Paper 2
// in June 2024 set grade A at 24 out of 40, which is 60%, not 80%.
//
// THIS PAPER'S BOUNDARY FIRST, THE AVERAGE ONLY AS A FALLBACK. A past paper
// names its own session and variant, so for most papers the published boundary
// is a dictionary lookup and there is nothing to average. bestThresholds()
// picks; the average covers the ~14% with no document (the June 2020 series was
// cancelled, and a few others are missing from the mirror). The difference is
// not cosmetic - see the worked example on sessionThresholdsFor().
//
// Multiple-choice thresholds run far lower than intuition suggests, because
// the mark scheme has no partial credit and chance contributes 25%. Grading a
// student against invented numbers would have cost them roughly two grades.
//
// NO A*. The source documents state that "Grade A* does not exist at the level
// of an individual component", so the component scale tops out at A - or at C
// on a Core-tier paper, which cannot award higher by design.
//
// THE RANGE IS THE POINT. A grade from 40 questions is a noisy estimate and a
// single letter implies a precision we do not have, so the band comes from the
// Wilson interval at 80% and the honest form is "B, could be A to C".
// --------------------------------------------------------------------------

/** Highest first. The order thresholds are searched in. */
export const GRADE_ORDER = ['A', 'B', 'C', 'D', 'E', 'F', 'G'] as const;
export type Grade = typeof GRADE_ORDER[number];

/** The published thresholds for a paper, or null if the scrape found none. */
export function thresholdsFor(
  subjectCode: string,
  paperNumber: number | null | undefined,
): PaperThresholds | null {
  if (paperNumber === null || paperNumber === undefined) return null;
  return PAPER_THRESHOLDS[`${subjectCode}/${paperNumber}`] ?? null;
}

/**
 * The thresholds Cambridge actually published for ONE exact paper.
 *
 * WHY THIS BEATS THE AVERAGE, ALWAYS, WHEN IT EXISTS. Thresholds move between
 * sessions because the papers differ in difficulty - that is the whole reason
 * Cambridge sets them per session rather than once. The average was only ever
 * a stand-in for a number we did not have. For a past paper we DO have it: the
 * schema names the session and the variant, so there is nothing to estimate.
 *
 * The spread being papered over is not small. IGCSE Physics Extended, June
 * 2024: grade A was 24 marks on variant 1, 25 on variant 2 and 27 on variant 3
 * - out of 40, within one session. A student on 25/40 was an A on two of those
 * papers and a B on the third, and the mean (26.4) calls them a B.
 *
 * Returns the same shape as thresholdsFor() so every function below - gradeAt,
 * isTierCapped, isPaperCeiling - works on it unchanged, with `session` set and
 * the spread fields at zero: there is no spread, because this is the boundary
 * rather than a guess at it.
 */
export function sessionThresholdsFor(
  paperId: string | null | undefined,
): PaperThresholds | null {
  if (!paperId) return null;
  const row = SESSION_THRESHOLDS[paperId];
  if (!row) return null;

  const [maxMark, ...marks] = row;
  const [code, series] = paperId.split('_');
  if (!code || !series) return null;
  const paper = paperNumberOf(paperId);
  if (paper === null) return null;

  const grades: PaperThresholds['grades'] = {};
  GRADE_ORDER.forEach((g, i) => {
    const mark = marks[i];
    // null is a grade the tier cannot award, not a grade at zero marks.
    if (mark === null || mark === undefined) return;
    const fraction = mark / maxMark;
    grades[g] = { mean: fraction, sd: 0, min: fraction, max: fraction, n: 1 };
  });

  const year = 2000 + Number(series.slice(1));
  const season = SEASON_NAMES[series[0] ?? ''] ?? series;
  return {
    code,
    paper,
    // The averaged row is the only place the qualification is recorded; the
    // threshold documents do not carry it per component.
    qualification: PAPER_THRESHOLDS[`${code}/${paper}`]?.qualification ?? '',
    maxMark,
    years: [year, year],
    session: `${season} ${year}`,
    grades,
  };
}

/**
 * Paper number from a schema: '0625_s24_21' -> 2.
 *
 * Duplicated from constants/subjectCodes.ts on purpose - that module pulls in
 * the whole subject-name table, and this file is imported by `node --test`
 * where the alias does not resolve. Two lines of arithmetic is the cheaper
 * duplication.
 */
function paperNumberOf(paperId: string): number | null {
  const field = paperId.split('_')[2];
  const digits = field?.match(/^\d+/)?.[0];
  if (!digits) return null;
  const n = digits.length >= 2 ? Number(digits[0]) : Number(digits);
  return Number.isFinite(n) && n > 0 ? n : null;
}

/** Where a set of thresholds came from. */
export type ThresholdBasis =
  /** This paper's own published boundaries. */
  | 'session'
  /** Mean across every session of this component we could find. */
  | 'average'
  /** Neither: nothing published that we could parse. */
  | 'none';

/**
 * The best thresholds available for a paper: its own if we have them, the
 * component average otherwise.
 *
 * Coverage of the session table is ~86% of the catalogue and cannot be
 * complete - the June 2020 series was cancelled, so for those papers no
 * threshold was ever set. The average is the fallback, and the basis is
 * returned rather than inferred so the UI can say which one it showed.
 */
export function bestThresholds(
  subjectCode: string,
  paperNumber: number | null | undefined,
  paperId?: string | null,
): { thresholds: PaperThresholds | null; basis: ThresholdBasis } {
  const exact = sessionThresholdsFor(paperId);
  if (exact) return { thresholds: exact, basis: 'session' };
  const mean = thresholdsFor(subjectCode, paperNumber);
  return { thresholds: mean, basis: mean ? 'average' : 'none' };
}

/**
 * The highest grade this paper can award, as a fraction of its marks.
 *
 * On a Core-tier IGCSE paper that is grade C, not grade A - the higher grades
 * are an en dash in the published table because the paper cannot award them.
 * Treating C as the ceiling there is not a concession; it IS the ceiling, and
 * a Core candidate scoring at it has nothing left to gain from the paper.
 */
export function masteryBar(
  subjectCode: string,
  paperNumber: number | null | undefined,
): number {
  const t = thresholdsFor(subjectCode, paperNumber);
  if (!t) return MODEL.mastery.fallbackMasteredAbove;
  for (const g of GRADE_ORDER) {
    const stat = t.grades[g];
    if (stat) return stat.mean;
  }
  return MODEL.mastery.fallbackMasteredAbove;
}

/** The grade a mark fraction earns on this paper. */
export function gradeAt(ratio: number, t: PaperThresholds | null): string {
  if (!t) return '?';
  for (const g of GRADE_ORDER) {
    const stat = t.grades[g];
    if (stat && ratio >= stat.mean) return g;
  }
  return 'U';
}

/**
 * Does this paper's tier stop it awarding the top grade?
 *
 * True for Core-tier IGCSE components, which cannot award above a C however
 * well the paper is answered. False for Extended and for untiered papers,
 * where the ceiling is grade A and is therefore not a limitation at all.
 *
 * The distinction matters for what we SAY. "You are at this paper's ceiling"
 * is useful advice on a Core paper - the same marks are worth more on
 * Extended - and is meaningless noise on a paper whose ceiling is an A.
 */
export function isTierCapped(t: PaperThresholds | null): boolean {
  return !!t && !t.grades.A;
}

/**
 * Is this the highest grade the paper can award?
 *
 * WHY THIS EXISTS. A Core-tier IGCSE paper cannot award above a C, so a
 * student scoring 83% on one is shown "C" - which looks like a broken app
 * rather than a fact about the paper. It is not a rounding artefact and it is
 * not harshness: it is the ceiling. Pair it with isTierCapped() before saying
 * anything to the student: hitting an A on Extended is also "the ceiling", and
 * telling someone who just got an A that they have hit a limit would be absurd.
 */
export function isPaperCeiling(grade: string, t: PaperThresholds | null): boolean {
  if (!t) return false;
  for (const g of GRADE_ORDER) {
    if (t.grades[g]) return g === grade;
  }
  return false;
}

/**
 * How a grade should READ - as a success, an adequate result, or a warning.
 *
 * A mapping and therefore a judgement, so it lives here with the rest of the
 * model rather than as a colour rule in a component. A/B is a strong pass, C/D
 * clears the bar most students are aiming at, E and below does not.
 *
 * This replaced a `percentage >= 80 ? 'strong' : percentage >= 60 ? 'fair'`
 * in the end-of-paper screen - invented cut-offs that, on a multiple-choice
 * component where grade A averages 66%, painted a genuine A as merely "fair".
 */
export function gradeTone(grade: string): 'strong' | 'fair' | 'weak' {
  if (grade === 'A' || grade === 'B') return 'strong';
  if (grade === 'C' || grade === 'D') return 'fair';
  return 'weak';
}

export interface Readiness {
  /** Best estimate. */
  grade: string;
  /** Grade at the top of the interval, and at the bottom. */
  best: string;
  worst: string;
  accuracy: Interval;
  marksAwarded: number;
  marksTotal: number;
  /** False until enough questions have been answered to say anything. */
  reliable: boolean;
  questions: number;
  /** Null when this paper has no published thresholds behind it. */
  thresholds: PaperThresholds | null;
  /**
   * Whether the grade was read off this paper's own published boundaries or
   * off the component average. The UI must say which: "a B on this paper" and
   * "a B on a paper of average difficulty" are different claims.
   */
  basis: ThresholdBasis;
  /**
   * Spread of the grade-boundary this estimate sits closest to, in marks
   * across sessions. Carried so the UI can say how much the boundary itself
   * moves - it is not a fixed line, and pretending otherwise is the same
   * mistake as reporting a point estimate.
   *
   * Null on a `session` basis, where the question does not arise: that
   * boundary did not move, it is the one that was published.
   */
  boundarySd: number | null;
}

/**
 * Component grade estimate with an honest band around it.
 *
 * Marks rather than question counts, because that is what a threshold is
 * expressed in and it is the definition of accuracy everywhere else in this
 * app (docs/solver/stats_page_design.md SS0.1).
 */
export function readiness(
  marksAwarded: number,
  marksTotal: number,
  questions: number,
  subjectCode: string,
  paperNumber: number | null | undefined,
  /**
   * The paper schema, when the marks came from ONE paper - '0625_s24_21'.
   * Given it, the grade is read off that paper's own published boundaries
   * instead of the component average. Omit it for a figure pooled across
   * several papers, where no single session's boundary applies.
   */
  paperId?: string | null,
): Readiness {
  const { thresholds: t, basis } = bestThresholds(subjectCode, paperNumber, paperId);
  const acc = wilson(marksAwarded, marksTotal, MODEL.grade.z);
  const grade = gradeAt(acc.point, t);
  const stat = t && grade !== 'U' && grade !== '?'
    ? t.grades[grade as Grade] ?? null
    : null;
  return {
    grade,
    best: gradeAt(acc.upper, t),
    worst: gradeAt(acc.lower, t),
    accuracy: acc,
    marksAwarded,
    marksTotal,
    reliable: questions >= MODEL.grade.minQuestions && marksTotal > 0 && t !== null,
    questions,
    thresholds: t,
    basis,
    boundarySd: basis === 'session' || !stat ? null : stat.sd,
  };
}

/**
 * Is this result short enough of the target grade to be worth nudging about?
 *
 * WHY THIS IS NOT A PERCENTAGE. The paper browser used to recommend more
 * practice to anyone averaging under 60% in a subject. On IGCSE Physics
 * Extended, 60% IS a grade A - so the browser was telling its strongest
 * candidates to go and practise more, in the same voice it used for a student
 * on an E. That is the identical error gradeTone() was written to remove from
 * the end-of-paper screen, and it survived here because the rule was a bare
 * number rather than a claim about grades.
 *
 * Expressed against the grade scale, it moves with the paper: on a Core-tier
 * component, where C is the ceiling, nothing above it can be called weak.
 */
export function needsPractice(grade: string): boolean {
  const target = GRADE_ORDER.indexOf(MODEL.flags.practiceBelowGrade as Grade);
  const got = GRADE_ORDER.indexOf(grade as Grade);
  // 'U' and '?' are not in the scale. U is below everything; '?' means we
  // have no thresholds and therefore no basis to tell anyone anything.
  if (grade === '?') return false;
  if (got === -1) return true;
  return got > target;
}

// --------------------------------------------------------------------------
// --------------------------------------------------------------------------
// SS G1. Behavioural flags - what one answered question looks like
//
// These three used to be CASE expressions inside v_question_flags. The view
// now reports the raw inputs and these decide, so the thresholds sit beside
// every other threshold in this file and can be retuned without a migration.
//
// All three are properties of ONE question. The *Rate constants in
// MODEL.flags are a different thing entirely: they decide whether a share of
// flagged questions is worth writing a sentence about.
// --------------------------------------------------------------------------

/** The columns of v_question_flags these rules read. */
export interface FlaggableQuestion {
  is_correct: boolean | null;
  confidence: number | null;
  time_spent_ms: number;
  median_time_ms: number;
  exploration_depth: number | null;
  eliminated_mask: number | null;
}

/**
 * Fast, no eliminations, essentially no interaction: a guess rather than a
 * decision.
 *
 * Correct guesses are the reason this exists - they inflate accuracy and hide
 * a gap that the accuracy figure says is not there.
 *
 * Measured against the PAPER'S OWN median rather than a fixed number of
 * seconds, because a question is only rushed relative to how long this student
 * spent on this paper. A null median cannot be compared against, so nothing is
 * claimed.
 */
export function isGuess(q: FlaggableQuestion): boolean {
  if (!q.median_time_ms) return false;
  return q.time_spent_ms < MODEL.flags.guessTimeRatio * q.median_time_ms
    && (q.exploration_depth ?? 0) <= MODEL.flags.guessExplorationMax
    && (q.eliminated_mask ?? 0) === 0;
}

/**
 * Confident and wrong - the questions a student will not think to revise,
 * because they do not know they got them wrong.
 *
 * Null confidence means the metrics for that question were never computed, so
 * there is no claim to make; `=== false` rather than `!is_correct` for the
 * same reason, since an unmarked question is not a wrong one.
 */
export function isOverconfident(q: FlaggableQuestion): boolean {
  return q.confidence !== null
    && q.confidence >= MODEL.flags.overconfidentAbove
    && q.is_correct === false;
}

/** Unsure and right - wasted time, or exam anxiety. */
export function isUnderconfident(q: FlaggableQuestion): boolean {
  return q.confidence !== null
    && q.confidence <= MODEL.flags.underconfidentBelow
    && q.is_correct === true;
}

// SS G2. Movement over time
//
// Two questions the dashboard and the stats page both ask: "am I getting
// better?" and "am I doing more than I was?". Both are differences between two
// windows, and both were previously computed inline in components - the
// accuracy trend existed TWICE, byte for byte, in StatsPage.vue and in
// Progress-Overall.vue, and the dashboard was about to need a third copy.
//
// Neither is a model in any real sense. They are here because they are
// arithmetic that makes a claim about the student, and because three copies of
// a definition is three chances for the page to contradict itself.
// --------------------------------------------------------------------------

/** The least an attempt has to carry for these to read it. */
export interface DatedAttempt {
  local_date: string;
  accuracy: number | null;
  questions_recorded: number | null;
  duration_ms: number | null;
}

/**
 * Change in accuracy, in ratio, between the newest papers and the oldest.
 *
 * NOT a fitted slope. A regression over a dozen noisy points would put a
 * confident line through something that is mostly variance; the difference of
 * two means is cruder and says only what it can support.
 *
 * Null below minPapersForTrend, because a handful of papers is a sample and
 * not a direction - see recommendations.ts, which refuses to phrase a trend
 * under the same rule.
 */
export function accuracyTrend(attempts: DatedAttempt[]): number | null {
  const chronological = attempts
    .filter(a => a.accuracy !== null)
    .sort((a, b) => a.local_date.localeCompare(b.local_date));
  // Strictly more than the minimum: at exactly five the two windows would
  // overlap, and a paper compared against itself always trends flat.
  if (chronological.length <= MODEL.flags.minPapersForTrend) return null;
  const take = Math.min(
    MODEL.flags.trendWindowPapers,
    Math.floor(chronological.length / 2));
  const mean = (xs: DatedAttempt[]) =>
    xs.reduce((n, a) => n + (a.accuracy ?? 0), 0) / xs.length;
  return mean(chronological.slice(-take)) - mean(chronological.slice(0, take));
}

/** A quantity now, the same quantity a window ago, and the difference. */
export interface Movement {
  current: number;
  previous: number;
  /** current - previous. Positive is more, which for all four is better. */
  delta: number;
  /** False when the earlier window is empty, so the delta is not a comparison. */
  comparable: boolean;
}

export interface RecentActivity {
  papers: Movement;
  questions: Movement;
  timeMs: Movement;
  /** Mean accuracy in ratio, so `delta` is a change in ratio, not in points. */
  accuracy: Movement;
}

/**
 * The last week against the week before it.
 *
 * WHY A DELTA AND NOT A TOTAL. A running total only ever goes up, so it says
 * nothing about whether the student is working now; "142 papers" reads the
 * same on a good week and after a month away. The comparison is what carries
 * the information, and it is the reference frame Jivet et al. (2020) call
 * self-referential - the student against their own past rather than against a
 * cohort we do not have.
 *
 * `comparable` is false when the earlier window is empty. Someone in their
 * first week is not "up 4 papers on last week"; they have no last week, and
 * dressing a starting total as growth would be a fabricated comparison.
 */
export function recentActivity(
  attempts: DatedAttempt[],
  today: string,
  windowDays: number = MODEL.flags.recentWindowDays,
): RecentActivity {
  const inWindow = (a: DatedAttempt, from: number, to: number) => {
    const age = daysBetween(a.local_date, today);
    return age >= from && age < to;
  };
  const now = attempts.filter(a => inWindow(a, 0, windowDays));
  const before = attempts.filter(a => inWindow(a, windowDays, windowDays * 2));

  const move = (
    current: number, previous: number, hadPrevious: boolean,
  ): Movement => ({
    current, previous, delta: current - previous, comparable: hadPrevious,
  });

  const sum = (xs: DatedAttempt[], f: (a: DatedAttempt) => number) =>
    xs.reduce((n, a) => n + f(a), 0);
  const meanAccuracy = (xs: DatedAttempt[]) => {
    const scored = xs.filter(a => a.accuracy !== null);
    return scored.length === 0
      ? 0
      : sum(scored, a => a.accuracy ?? 0) / scored.length;
  };

  const hadPrevious = before.length > 0;
  return {
    papers: move(now.length, before.length, hadPrevious),
    questions: move(
      sum(now, a => a.questions_recorded ?? 0),
      sum(before, a => a.questions_recorded ?? 0), hadPrevious),
    timeMs: move(
      sum(now, a => a.duration_ms ?? 0),
      sum(before, a => a.duration_ms ?? 0), hadPrevious),
    accuracy: move(
      meanAccuracy(now), meanAccuracy(before),
      // An earlier window with papers but none of them marked cannot be
      // compared on accuracy even though it can be compared on count.
      before.some(a => a.accuracy !== null)),
  };
}

// --------------------------------------------------------------------------
// SS H. Assembly
//
// The one function that turns raw practice rows into a reading. Kept here
// rather than in the composable so that no caller can assemble the pieces in
// a different order and get a different answer.
// --------------------------------------------------------------------------

export interface PracticeRow {
  topic_id: string;
  topic_name: string;
  subject_code: string;
  is_correct: boolean;
  option_count: number;
  marks: number;
  local_date: string;
  started_at: string;
  paper_id: string;
  paper_number: number | null;
  question_number: number;
}

/** Builds a TopicReading from one topic's practice rows. `today` is ISO date. */
export function readTopic(rows: PracticeRow[], today: string): TopicReading {
  const ordered = [...rows].sort((a, b) => a.started_at.localeCompare(b.started_at));
  const correct = ordered.filter(r => r.is_correct).length;
  const questions = ordered.length;

  const mastery = recencyWeightedAccuracy(
    ordered.map(r => ({ isCorrect: r.is_correct, optionCount: r.option_count })),
  );
  const accuracy = wilson(correct, questions);

  // Modal option count and modal paper: the chance level this topic is usually
  // asked at, and the component whose thresholds apply to it. A topic can
  // appear on both the Core and Extended paper of a syllabus, and those have
  // different ceilings, so the mode is the honest single answer.
  const optionCount = modeOf(ordered.map(r => r.option_count)) ?? 4;
  const paperNumber = modeOf(
    ordered.map(r => r.paper_number).filter((n): n is number => n !== null));
  const subjectCode = ordered[0]?.subject_code ?? '';
  const bar = masteryBar(subjectCode, paperNumber);

  const lastDate = ordered[ordered.length - 1]?.local_date ?? null;
  const daysSincePractice = lastDate === null ? null : daysBetween(lastDate, today);

  return {
    mastery,
    accuracy,
    questions,
    optionCount,
    bar,
    band: bandOf(accuracy, questions, optionCount, bar),
    retention: daysSincePractice === null
      ? 0
      : retention(daysSincePractice, correct, questions - correct),
    daysSincePractice,
    marksAwarded: ordered.reduce((n, r) => n + (r.is_correct ? r.marks : 0), 0),
    marksTotal: ordered.reduce((n, r) => n + r.marks, 0),
  };
}

/** Most frequent value, or null for an empty list. Ties break on first seen. */
function modeOf<T>(values: T[]): T | null {
  const counts = new Map<T, number>();
  for (const v of values) counts.set(v, (counts.get(v) ?? 0) + 1);
  let best: T | null = null;
  let bestN = 0;
  for (const [v, n] of counts) if (n > bestN) { best = v; bestN = n; }
  return best;
}

/** Groups practice rows by topic and returns the ranked revision queue. */
export function buildQueue(rows: PracticeRow[], today: string): QueueItem[] {
  const byTopic = new Map<string, PracticeRow[]>();
  for (const r of rows) {
    const list = byTopic.get(r.topic_id);
    if (list) list.push(r); else byTopic.set(r.topic_id, [r]);
  }

  const marksByTopic = new Map<string, number>();
  for (const [id, list] of byTopic) {
    marksByTopic.set(id, list.reduce((n, r) => n + r.marks, 0));
  }
  // Normalised against the largest topic rather than the total, so the term
  // spans [0,1] regardless of how many topics are in the selection.
  const maxMarks = Math.max(1, ...marksByTopic.values());

  return [...byTopic.entries()]
    .map(([topicId, list]) => revisionPriority({
      topicId,
      topicName: list[0]!.topic_name,
      subjectCode: list[0]!.subject_code,
      reading: readTopic(list, today),
      marksShare: (marksByTopic.get(topicId) ?? 0) / maxMarks,
    }))
    .sort((a, b) => b.score - a.score);
}

/**
 * Every question the student got wrong, most-worth-redoing first.
 *
 * Ordered by the priority of the topic it belongs to rather than by date: the
 * point is not to review the most recent mistakes but the ones sitting on the
 * cheapest marks. Practice testing is the highest-utility technique in
 * Dunlosky et al. (2013); this is the set to practise on.
 */
export interface MissedQuestion {
  paperId: string;
  questionNumber: number;
  topicId: string;
  topicName: string;
  subjectCode: string;
  localDate: string;
  marks: number;
  /** Priority of the owning topic, for ordering and for the UI's reason chip. */
  topicScore: number;
}

export function missedQuestions(rows: PracticeRow[], queue: QueueItem[]): MissedQuestion[] {
  const scoreByTopic = new Map(queue.map(q => [q.topicId, q.score]));
  const seen = new Set<string>();
  const out: MissedQuestion[] = [];

  for (const r of rows) {
    if (r.is_correct) continue;
    // A question tagged with two topics is one question, not two, so the
    // paper/question pair is deduplicated - it keeps whichever topic ranks
    // highest, which is the one the student should be told about.
    const key = `${r.paper_id}#${r.question_number}`;
    const score = scoreByTopic.get(r.topic_id) ?? 0;
    const existing = out.find(m => `${m.paperId}#${m.questionNumber}` === key);
    if (existing) {
      if (score > existing.topicScore) {
        existing.topicId = r.topic_id;
        existing.topicName = r.topic_name;
        existing.topicScore = score;
      }
      continue;
    }
    seen.add(key);
    out.push({
      paperId: r.paper_id,
      questionNumber: r.question_number,
      topicId: r.topic_id,
      topicName: r.topic_name,
      subjectCode: r.subject_code,
      localDate: r.local_date,
      marks: r.marks,
      topicScore: score,
    });
  }

  return out.sort((a, b) => b.topicScore - a.topicScore
    || b.localDate.localeCompare(a.localDate));
}

// --------------------------------------------------------------------------
// SS I. The pseudocode IDE
//
// The IDE and the solver measure different things and must not be averaged
// together. A multiple-choice question is right or wrong against one key; a
// pseudocode answer is marked against a rubric of marking points and can be
// half right. docs/roadmap.md A4 records the consequence of blurring them:
// "accuracy" on the stats page silently meant MCQ accuracy. These figures are
// therefore reported as their own section, never folded into the solver's.
//
// Everything here reads the append-only ide_attempts log (migration
// 00000000000006). None of it is derivable from ide_progress, which keeps only
// the best score per question.
// --------------------------------------------------------------------------

/** One row of the ide_attempts log, as much of it as these functions need. */
export interface IdeSubmission {
  record_id: string;
  score: number;
  max_marks: number;
  local_date: string;
  created_at: string;
}

/** The v_ide_stats row. Null for a student who has never submitted. */
export interface IdeTotals {
  attempted: number;
  solved: number;
  submissions: number;
  best_marks: number;
  best_marks_possible: number;
}

export interface IdeReading {
  attempted: number;
  solved: number;
  submissions: number;
  marksAwarded: number;
  marksPossible: number;
  /** Submissions spent per question solved. Null with nothing solved yet. */
  submissionsPerSolve: number | null;
  /** Questions solved on the very first submission. */
  firstTrySolves: number;
  /** firstTrySolves / solved, or null when it cannot be stated honestly. */
  firstTryRate: number | null;
  /** Change in per-submission accuracy, newest against oldest. */
  trend: number | null;
  /**
   * Whether the log covers every question the totals count.
   *
   * The log query is capped, so a long history arrives truncated. When it does,
   * the rates above are computed over a biased sample - the OLDEST submissions,
   * because the log is read oldest-first - which would understate a student who
   * has since improved. The rates are withheld rather than reported wrong.
   */
  complete: boolean;
}

/**
 * The IDE's reading.
 *
 * The headline counts come from the view, which sees every row; the shape
 * comes from the log, which is capped. Mixing the two sources is deliberate:
 * an under-counted total would be visibly wrong, whereas a rate computed over
 * a truncated sample would look perfectly plausible and be wrong anyway.
 */
export function readIde(
  totals: IdeTotals | null,
  submissions: IdeSubmission[],
): IdeReading {
  const empty: IdeReading = {
    attempted: 0, solved: 0, submissions: 0,
    marksAwarded: 0, marksPossible: 0,
    submissionsPerSolve: null, firstTrySolves: 0, firstTryRate: null,
    trend: null, complete: true,
  };
  if (!totals) return empty;

  // Oldest first, so "the first submission" is the first element per question.
  const chronological = [...submissions].sort(
    (a, b) => a.created_at.localeCompare(b.created_at));

  const byQuestion = new Map<string, IdeSubmission[]>();
  for (const s of chronological) {
    const list = byQuestion.get(s.record_id);
    if (list) list.push(s);
    else byQuestion.set(s.record_id, [s]);
  }

  const complete = byQuestion.size >= totals.attempted;

  let firstTrySolves = 0;
  for (const list of byQuestion.values()) {
    const first = list[0]!;
    if (first.max_marks > 0 && first.score >= first.max_marks) firstTrySolves += 1;
  }

  return {
    attempted: totals.attempted,
    solved: totals.solved,
    submissions: totals.submissions,
    marksAwarded: totals.best_marks,
    marksPossible: totals.best_marks_possible,
    submissionsPerSolve: totals.solved > 0
      ? totals.submissions / totals.solved
      : null,
    firstTrySolves,
    firstTryRate: complete && totals.solved > 0
      ? firstTrySolves / totals.solved
      : null,
    trend: accuracyTrend(chronological.map(s => ({
      local_date: s.local_date,
      // A question worth no marks carries no accuracy; accuracyTrend drops it.
      accuracy: s.max_marks > 0 ? s.score / s.max_marks : null,
      questions_recorded: null,
      duration_ms: null,
    }))),
    complete,
  };
}
