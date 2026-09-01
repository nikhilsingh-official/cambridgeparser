//
// This file exists because model.ts makes CLAIMS ABOUT A STUDENT. A chart that
// renders wrong looks wrong; a mastery estimate that is wrong looks exactly
// like one that is right, and the student acts on it. The formulas below are
// checked against published values where published values exist, and against
// their own stated properties where they do not.
//
// Run: npm run test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  MODEL, wilson, recencyWeightedAccuracy, chanceLevel, halfLifeDays, retention,
  daysBetween, isFading, proximity, bandOf, Band, revisionPriority, readiness,
  gradeAt, GRADE_ORDER, thresholdsFor, masteryBar, gradeTone, isPaperCeiling, isTierCapped,
  sessionThresholdsFor, bestThresholds, needsPractice,
  accuracyTrend, recentActivity, readIde,
  isGuess, isOverconfident, isUnderconfident, type FlaggableQuestion,
  readTopic, buildQueue, missedQuestions,
  type PracticeRow, type DatedAttempt,
} from '../src/lib/stats/model.ts';
import { PAPER_THRESHOLDS, SESSION_THRESHOLDS } from '../src/constants/gradeThresholds.ts';
import { paperNumberFromSchema, subjectCodeFromSchema } from '../src/constants/subjectCodes.ts';

// The real published bar for IGCSE Physics Extended Paper 2. Named rather than
// hard-coded so these tests keep testing the model when the scrape is re-run.
const BAR = masteryBar('0625', 2);

const close = (a: number, b: number, eps = 1e-4) =>
  assert.ok(Math.abs(a - b) < eps, `expected ${a} ~= ${b}`);

// --------------------------------------------------------------- SS A Wilson

// The published Wilson interval for 8 successes in 10 trials at 95% is
// (0.4901, 0.9433). If this drifts, the interval is not Wilson's any more.
test('wilson matches the published interval for 8/10 at 95%', () => {
  const w = wilson(8, 10);
  close(w.lower, 0.4901);
  close(w.upper, 0.9433);
  close(w.point, 0.8);
});

test('wilson stays inside [0,1] at the extremes, where Wald does not', () => {
  const perfect = wilson(5, 5);
  assert.ok(perfect.upper <= 1);
  assert.ok(perfect.lower > 0 && perfect.lower < 1,
    'a 5-for-5 run must not certify mastery');
  const none = wilson(0, 5);
  assert.ok(none.lower >= 0);
  assert.ok(none.upper > 0, 'zero-for-five is not proof of zero knowledge');
});

test('wilson is symmetric under swapping successes for failures', () => {
  const a = wilson(3, 10);
  const b = wilson(7, 10);
  close(a.lower, 1 - b.upper);
  close(a.upper, 1 - b.lower);
});

test('wilson narrows as evidence accumulates', () => {
  const widths = [5, 20, 100, 500].map(n => wilson(Math.round(n * 0.7), n).width);
  for (let i = 1; i < widths.length; i++) {
    assert.ok(widths[i]! < widths[i - 1]!, 'more trials must mean less uncertainty');
  }
});

test('wilson on no trials admits it knows nothing', () => {
  const w = wilson(0, 0);
  assert.equal(w.lower, 0);
  assert.equal(w.upper, 1);
});

// ------------------------------------------------- SS B recency-weighted mastery
//
// These tests encode why BKT is NOT in model.ts. The order-sensitivity
// property is the one that made BKT attractive and it is preserved here; the
// saturation that made BKT unusable at topic grain is what the last test
// guards against.

const trials = (pattern: string, optionCount = 4) =>
  [...pattern].map(c => ({ isCorrect: c === '1', optionCount }));

test('mastery is null with no evidence, not zero', () => {
  assert.equal(recencyWeightedAccuracy([]), null,
    'no evidence and total failure are different claims');
});

test('mastery is the plain ratio when every answer is equally recent', () => {
  close(recencyWeightedAccuracy(trials('1111'))!, 1);
  close(recencyWeightedAccuracy(trials('0000'))!, 0);
});

// THE PROPERTY THAT A PLAIN RATIO CANNOT EXPRESS. Both sequences are 2-for-4
// and they describe opposite students.
test('mastery reads order - improving beats declining at the same ratio', () => {
  const improving = recencyWeightedAccuracy(trials('0011'))!;
  const declining = recencyWeightedAccuracy(trials('1100'))!;
  assert.ok(improving > declining,
    `improving ${improving} must exceed declining ${declining} at equal accuracy`);
});

test('mastery stays a probability under any sequence', () => {
  for (const p of ['1', '0', '10101010', '1111111111', '0000000000']) {
    const m = recencyWeightedAccuracy(trials(p))!;
    assert.ok(m >= 0 && m <= 1, `mastery ${m} out of range for "${p}"`);
  }
});

// THE REGRESSION. BKT reported P(L) ~ 1.0 for a topic answered at 70%, which
// is what took it out of the model. Whatever replaces this must not saturate.
test('mastery does not saturate on a long imperfect run', () => {
  const seq = Array.from({ length: 60 }, (_, i) => i % 10 < 7 ? '1' : '0').join('');
  const m = recencyWeightedAccuracy(trials(seq))!;
  assert.ok(m > 0.55 && m < 0.85,
    `a 70% run must read near 70%, not ${m.toFixed(2)}`);
});

test('recent evidence outweighs old evidence', () => {
  const lambda = MODEL.mastery.recencyHalfLifeQuestions;
  const oldWins = '1'.repeat(lambda * 3) + '0'.repeat(lambda);
  const m = recencyWeightedAccuracy(trials(oldWins))!;
  const ratio = (lambda * 3) / (lambda * 4);
  assert.ok(m < ratio, `recent failures must drag the estimate below the raw ratio ${ratio}`);
});

test('chanceLevel is structural and floors at a two-option question', () => {
  close(chanceLevel(4), 0.25);
  close(chanceLevel(5), 0.2);
  close(chanceLevel(1), 0.5, 1e-9);
});

// ---------------------------------------------------------------- SS C decay

// Settles & Meeder eq. 1 defines the half-life as the lag at which recall is
// exactly one half. If this fails, "half-life" is a lie in the variable name.
test('retention is 1 at zero lag and 0.5 at exactly one half-life', () => {
  close(retention(0, 10, 2), 1);
  const h = halfLifeDays(10, 2);
  close(retention(h, 10, 2), 0.5);
  close(retention(2 * h, 10, 2), 0.25);
});

test('half-life grows with success and shrinks with failure', () => {
  assert.ok(halfLifeDays(20, 0) > halfLifeDays(5, 0));
  assert.ok(halfLifeDays(10, 10) < halfLifeDays(10, 0));
});

test('half-life stays inside its clamp', () => {
  assert.ok(halfLifeDays(0, 500) >= MODEL.decay.minHalfLifeDays);
  assert.ok(halfLifeDays(10_000, 0) <= MODEL.decay.maxHalfLifeDays);
});

test('isFading fires exactly at the half-life, not before', () => {
  const h = halfLifeDays(10, 2);
  assert.equal(isFading(retention(h - 0.01, 10, 2)), false);
  assert.equal(isFading(retention(h + 0.01, 10, 2)), true);
});

test('daysBetween counts whole local days and never goes negative', () => {
  assert.equal(daysBetween('2026-08-01', '2026-08-22'), 21);
  assert.equal(daysBetween('2026-08-22', '2026-08-01'), 0);
  assert.equal(daysBetween('2026-08-22', '2026-08-22'), 0);
});

// ------------------------------------------------------------- SS D banding

test('proximity peaks between chance and the paper bar, zero at both edges', () => {
  const lo = chanceLevel(4);
  close(proximity((lo + BAR) / 2, 4, BAR), 1);
  close(proximity(lo, 4, BAR), 0);
  close(proximity(BAR, 4, BAR), 0);
});

test('a topic with no evidence sits at the peak, so the queue raises it', () => {
  close(proximity(null, 4, BAR), 1);
});

test('a topic with too little evidence is untested, not bad', () => {
  const few = MODEL.queue.minQuestions - 1;
  assert.equal(bandOf(wilson(0, few), few, 4, BAR), Band.Untested);
});

test('a topic indistinguishable from guessing is struggling, not proximal', () => {
  const acc = wilson(5, 20);
  assert.ok(acc.lower <= chanceLevel(4), 'test premise: lower bound at or below chance');
  assert.equal(bandOf(acc, 20, 4, BAR), Band.Struggling);
});

// The band tests use the interval BOUND, so a short hot streak is not mastery.
test('mastery has to survive its own error bars', () => {
  assert.equal(bandOf(wilson(6, 8), 8, 4, BAR), Band.Proximal,
    '6-for-8 is too little evidence to certify the top grade');
  assert.equal(bandOf(wilson(95, 100), 100, 4, BAR), Band.Mastered);
});

test('a middling topic with real evidence is proximal', () => {
  assert.equal(bandOf(wilson(20, 40), 40, 4, BAR), Band.Proximal);
});

// A Core-tier paper cannot award above a C, so its ceiling is the C threshold
// and a student at it has nothing further to gain from that paper.
test('the mastery bar is the top grade the PAPER can award', () => {
  const core = masteryBar('0625', 1);
  const extended = masteryBar('0625', 2);
  assert.ok(core > 0 && extended > 0, 'both papers must have scraped thresholds');
  assert.ok(!PAPER_THRESHOLDS['0625/1']!.grades.A,
    'test premise: Core paper 1 has no grade A');
  assert.ok(PAPER_THRESHOLDS['0625/2']!.grades.A, 'Extended paper 2 has grade A');
});

test('an unknown paper falls back rather than throwing', () => {
  assert.equal(thresholdsFor('9999', 1), null);
  close(masteryBar('9999', 1), MODEL.mastery.fallbackMasteredAbove);
  close(masteryBar('0625', null), MODEL.mastery.fallbackMasteredAbove);
});

// ---------------------------------------------------------------- SS E queue

const reading = (mastery: number, ret: number) => ({
  mastery, retention: ret, accuracy: wilson(5, 10), questions: 10,
  optionCount: 4, bar: BAR, band: Band.Proximal, daysSincePractice: 3,
  marksAwarded: 5, marksTotal: 10,
});
const CHANCE = chanceLevel(4);

test('queue score stays in [0,1] and its terms sum to it', () => {
  for (const m of [0, CHANCE, (CHANCE + BAR) / 2, BAR, 1]) {
    for (const r of [0, 0.5, 1]) {
      const q = revisionPriority({
        topicId: 't', topicName: 'T', subjectCode: '0625',
        reading: reading(m, r), marksShare: 0.5,
      });
      assert.ok(q.score >= 0 && q.score <= 1, `score ${q.score} out of range`);
      close(q.terms.gap + q.terms.decay + q.terms.marks, q.score);
    }
  }
});

test('the queue weights sum to one, or the score is not a percentage', () => {
  close(MODEL.queue.wGap + MODEL.queue.wDecay + MODEL.queue.wMarks, 1);
});

// The design decision recorded in SS E: a sum, not a product, so maintenance
// of a mastered topic is still possible.
test('a mastered but faded topic still surfaces', () => {
  const fresh = revisionPriority({
    topicId: 'a', topicName: 'A', subjectCode: '0625',
    reading: reading(BAR, 1), marksShare: 0.5,
  });
  const faded = revisionPriority({
    topicId: 'b', topicName: 'B', subjectCode: '0625',
    reading: reading(BAR, 0.05), marksShare: 0.5,
  });
  assert.ok(faded.score > fresh.score);
  assert.equal(faded.driver, 'decay', 'and the UI must be able to say why');
});

test('a proximal topic outranks a hopeless one at equal decay', () => {
  const proximal = revisionPriority({
    topicId: 'a', topicName: 'A', subjectCode: '0625',
    reading: reading((CHANCE + BAR) / 2, 0.5), marksShare: 0.5,
  });
  const hopeless = revisionPriority({
    topicId: 'b', topicName: 'B', subjectCode: '0625',
    reading: reading(CHANCE, 0.5), marksShare: 0.5,
  });
  assert.ok(proximal.score > hopeless.score,
    'sending a student at what they cannot yet learn is the ROPL failure mode');
});

// ------------------------------------------------------------- SS F grades

test('the scraped thresholds are internally consistent', () => {
  assert.ok(Object.keys(PAPER_THRESHOLDS).length >= 10,
    'the scrape should have found most catalogue papers');
  for (const [key, t] of Object.entries(PAPER_THRESHOLDS)) {
    const present = GRADE_ORDER.filter(g => t.grades[g]);
    assert.ok(present.length >= 3, `${key} has too few grades`);
    // Thresholds must descend with the grade, or the scale is misaligned.
    for (let i = 1; i < present.length; i++) {
      assert.ok(t.grades[present[i]!]!.mean < t.grades[present[i - 1]!]!.mean,
        `${key}: ${present[i]} is not below ${present[i - 1]}`);
    }
    for (const g of present) {
      const st = t.grades[g]!;
      assert.ok(st.mean > 0 && st.mean < 1, `${key} ${g}: mean ${st.mean} out of range`);
      assert.ok(st.min <= st.mean && st.mean <= st.max, `${key} ${g}: mean outside min/max`);
      assert.ok(st.n > 0);
    }
    // A grade with no A is a Core-tier paper, which must also have no B.
    if (!t.grades.A) assert.ok(!t.grades.B, `${key} has B but no A`);
  }
});

// THE FINDING THAT MOTIVATED THE SCRAPE. The model previously graded against
// "typical" percentages with A at 80%. Real multiple-choice thresholds run far
// lower, because there is no partial credit and chance contributes 25%.
test('real multiple-choice grade A is nowhere near 80%', () => {
  const a = PAPER_THRESHOLDS['0625/2']!.grades.A!;
  assert.ok(a.mean < 0.75,
    `IGCSE Physics P2 grade A averages ${(a.mean * 100).toFixed(1)}% - if this ` +
    'ever reaches 80% the scrape or the averaging has broken');
});

test('gradeAt walks the scraped scale and bottoms out at U', () => {
  const t = PAPER_THRESHOLDS['0625/2']!;
  assert.equal(gradeAt(1, t), 'A');
  assert.equal(gradeAt(0, t), 'U');
  assert.equal(gradeAt(t.grades.C!.mean, t), 'C');
  assert.equal(gradeAt(t.grades.C!.mean - 0.0001, t), 'D');
});

test('gradeAt on a paper with no thresholds refuses to guess', () => {
  assert.equal(gradeAt(0.9, null), '?');
});

test('readiness reports a band, and the band contains the estimate', () => {
  const r = readiness(30, 40, 40, '0625', 2);
  assert.ok(r.accuracy.lower <= r.accuracy.point && r.accuracy.point <= r.accuracy.upper);
  const order = [...GRADE_ORDER, 'U'] as string[];
  assert.ok(order.indexOf(r.best) <= order.indexOf(r.grade));
  assert.ok(order.indexOf(r.grade) <= order.indexOf(r.worst));
});

test('readiness refuses to be read at small n or without thresholds', () => {
  assert.equal(readiness(8, 10, 10, '0625', 2).reliable, false);
  assert.equal(readiness(32, 40, 40, '0625', 2).reliable, true);
  assert.equal(readiness(32, 40, 40, '9999', 1).reliable, false);
});

// ------------------------------------------- SS F session-exact thresholds
//
// A past paper names its own session and variant, so its published boundary is
// a lookup rather than an estimate. These guard that the lookup is preferred,
// that the fallback still works where no document exists, and that the scraped
// session rows are self-consistent.

test('the session table is internally consistent', () => {
  const keys = Object.keys(SESSION_THRESHOLDS);
  assert.ok(keys.length > 1000, `only ${keys.length} session rows - scrape shrank`);
  for (const key of keys) {
    const [maxMark, ...marks] = SESSION_THRESHOLDS[key]!;
    assert.ok(maxMark > 0, `${key}: max mark ${maxMark}`);
    const present = marks.filter((m): m is number => m !== null);
    assert.ok(present.length >= 3, `${key} offers too few grades`);
    for (const m of present) {
      assert.ok(m > 0 && m <= maxMark, `${key}: threshold ${m} of ${maxMark}`);
    }
    for (let i = 1; i < present.length; i++) {
      assert.ok(present[i]! < present[i - 1]!, `${key}: grades do not descend`);
    }
    // The awarded grades are one unbroken run. Nulls are legitimate at BOTH
    // ends - above, where a Core-tier paper cannot award an A, and below,
    // where the table simply stops (O Level Economics publishes A-E and no
    // F or G at all). A null BETWEEN two awarded grades would mean a column
    // was misread, which is the thing worth failing on.
    const first = marks.findIndex(m => m !== null);
    const last = marks.length - 1 - [...marks].reverse().findIndex(m => m !== null);
    assert.ok(marks.slice(first, last + 1).every(m => m !== null),
      `${key}: a gap in the middle of the grade scale`);
  }
});

test('sessionThresholdsFor expands a row into the same shape as the average', () => {
  const t = sessionThresholdsFor('0625_s24_21')!;
  assert.equal(t.code, '0625');
  assert.equal(t.paper, 2, 'component 21 is Paper 2');
  assert.equal(t.maxMark, 40);
  assert.equal(t.session, 'June 2024');
  assert.deepEqual(t.years, [2024, 2024]);
  // The document itself: grade A was 24 out of 40.
  assert.equal(t.grades.A!.mean, 24 / 40);
  // No spread, because this is the boundary rather than a guess at it.
  assert.equal(t.grades.A!.sd, 0);
  assert.equal(t.grades.A!.min, t.grades.A!.max);
  assert.equal(t.grades.A!.n, 1);
});

test('a Core-tier session row carries no A or B', () => {
  const t = sessionThresholdsFor('0625_s24_11')!;
  assert.equal(t.paper, 1);
  assert.equal(t.grades.A, undefined, 'a Core paper cannot award an A');
  assert.equal(t.grades.B, undefined);
  assert.ok(t.grades.C, 'and C is its ceiling');
  assert.equal(isTierCapped(t), true);
});

test('sessionThresholdsFor returns null rather than inventing a paper', () => {
  assert.equal(sessionThresholdsFor('0625_s99_21'), null);
  assert.equal(sessionThresholdsFor('9999_s24_11'), null);
  assert.equal(sessionThresholdsFor(''), null);
  assert.equal(sessionThresholdsFor(null), null);
  assert.equal(sessionThresholdsFor('nonsense'), null);
});

test('bestThresholds prefers the paper own boundary over the average', () => {
  const { thresholds, basis } = bestThresholds('0625', 2, '0625_s24_21');
  assert.equal(basis, 'session');
  assert.equal(thresholds!.session, 'June 2024');
  assert.notEqual(thresholds!.grades.A!.mean, PAPER_THRESHOLDS['0625/2']!.grades.A!.mean,
    'if these ever match, the session lookup is silently falling through');
});

// June 2020 was cancelled, so no threshold was ever published for it. That is
// exactly the case the average exists to cover.
test('bestThresholds falls back to the average for a session with no document', () => {
  assert.equal(SESSION_THRESHOLDS['0625_s20_21'], undefined,
    'the June 2020 series was cancelled - no paper, no threshold');
  const { thresholds, basis } = bestThresholds('0625', 2, '0625_s20_21');
  assert.equal(basis, 'average');
  assert.equal(thresholds!.session, undefined);
  assert.equal(thresholds, PAPER_THRESHOLDS['0625/2']);
});

test('bestThresholds reports none when nothing is published either way', () => {
  const { thresholds, basis } = bestThresholds('9999', 1, '9999_s24_11');
  assert.equal(basis, 'none');
  assert.equal(thresholds, null);
});

// WHY THE EXACT BOUNDARY IS WORTH THE 45KB. Within June 2024 alone, grade A on
// IGCSE Physics Extended was 24, 25 and 27 marks across variants 21, 22 and 23.
// A student on 25/40 sat an A paper or a B paper depending which they opened,
// and the mean calls it one thing for all three.
test('the same marks earn different grades on different variants of one session', () => {
  const grades = ['0625_s24_21', '0625_s24_22', '0625_s24_23']
    .map(id => readiness(25, 40, 40, '0625', 2, id).grade);
  assert.deepEqual(grades, ['A', 'A', 'B']);
  assert.equal(readiness(25, 40, 40, '0625', 2).grade, 'B',
    'and the average alone would have called all three a B');
});

test('readiness records which boundary it used', () => {
  assert.equal(readiness(30, 40, 40, '0625', 2, '0625_s24_21').basis, 'session');
  assert.equal(readiness(30, 40, 40, '0625', 2).basis, 'average');
  assert.equal(readiness(30, 40, 40, '9999', 1).basis, 'none');
});

// The spread is a property of averaging. On a session row there is nothing to
// spread, and reporting a 0 would invite the UI to print "±0 marks".
test('boundarySd is null on a session basis and real on an average', () => {
  assert.equal(readiness(30, 40, 40, '0625', 2, '0625_s24_21').boundarySd, null);
  assert.ok(readiness(30, 40, 40, '0625', 2).boundarySd! > 0);
});

// Pooled figures must NOT get a session boundary even if one is passed by
// mistake - but the guard is at the call site, so this just pins the contract
// that omitting the id is what selects the average.
test('omitting the paper id selects the average, as pooled callers rely on', () => {
  const pooled = readiness(60, 80, 80, '0625', 2);
  assert.equal(pooled.basis, 'average');
  assert.equal(pooled.thresholds, PAPER_THRESHOLDS['0625/2']);
});

// THE BUG THIS RULE REPLACED. The paper browser recommended more practice to
// anyone averaging under 60% in a subject. Grade C on IGCSE Physics CORE
// averages 57.2%, and C is the highest that paper can award - so a candidate
// who had maxed out the grade scale was told to go and practise.
test('needsPractice cannot flag a student at the top of the paper scale', () => {
  const r = readiness(23, 40, 40, '0625', 1);
  assert.equal(r.grade, 'C');
  assert.equal(isPaperCeiling(r.grade, r.thresholds), true, 'C is all this paper offers');
  assert.ok(r.accuracy.point < 0.60, 'and it is under 60% - the old rule fired here');
  assert.equal(needsPractice(r.grade), false);
});

// 32 of the scraped session papers set grade A below 60%, so the old rule also
// flagged outright A candidates on the papers where the threshold ran lowest.
test('needsPractice leaves a grade A alone even at 52% of the marks', () => {
  const r = readiness(22, 40, 40, '0625', 2, '0625_s21_21');
  assert.equal(r.basis, 'session');
  assert.equal(r.grade, 'A', 'grade A on this paper was 21 out of 40');
  assert.ok(r.accuracy.point < 0.60);
  assert.equal(needsPractice(r.grade), false);
});

test('needsPractice fires below the target grade and not at or above it', () => {
  assert.equal(needsPractice('A'), false);
  assert.equal(needsPractice('B'), false);
  assert.equal(needsPractice('C'), false, 'C is the target, not below it');
  assert.equal(needsPractice('D'), true);
  assert.equal(needsPractice('U'), true, 'U is below every grade in the scale');
});

test('needsPractice says nothing when there are no thresholds to say it from', () => {
  assert.equal(needsPractice('?'), false);
});

// On a Core paper C is the ceiling, so nothing it can award counts as weak.
test('needsPractice cannot call a Core paper ceiling weak', () => {
  const t = sessionThresholdsFor('0625_s24_11')!;
  assert.equal(gradeAt(1, t), 'C', 'C is the best this paper awards');
  assert.equal(needsPractice('C'), false);
});

// The end-of-paper screen has only the schema string to work from, so this
// parse is what decides which threshold scale an attempt is graded against.
// Getting it wrong grades an Extended paper on the Core scale, silently.
test('paperNumberFromSchema reads the component out of a schema', () => {
  assert.equal(paperNumberFromSchema('0625_s25_22'), 2);
  assert.equal(paperNumberFromSchema('0625_s24_11'), 1);
  assert.equal(paperNumberFromSchema('9702_w23_13'), 1);
  assert.equal(paperNumberFromSchema('5054_w16_1'), 1, 'bare paper number, no variant');
  assert.equal(paperNumberFromSchema('0610_m24_42'), 4);
});

test('paperNumberFromSchema returns null rather than guessing', () => {
  assert.equal(paperNumberFromSchema('0625_s25'), null);
  assert.equal(paperNumberFromSchema('nonsense'), null);
  assert.equal(paperNumberFromSchema(''), null);
  assert.equal(paperNumberFromSchema('0625_s25_qp'), null);
});

test('a schema string grades against its own component', () => {
  const schema = '0625_s24_21';   // Physics, Extended
  const t = thresholdsFor(subjectCodeFromSchema(schema), paperNumberFromSchema(schema));
  assert.ok(t?.grades.A, 'Extended paper 2 can award an A');
  const core = thresholdsFor('0625', paperNumberFromSchema('0625_s24_11'));
  assert.ok(core && !core.grades.A, 'Core paper 1 cannot');
});

test('gradeTone maps the letter, not the percentage', () => {
  assert.equal(gradeTone('A'), 'strong');
  assert.equal(gradeTone('B'), 'strong');
  assert.equal(gradeTone('C'), 'fair');
  assert.equal(gradeTone('E'), 'weak');
  assert.equal(gradeTone('U'), 'weak');
  assert.equal(gradeTone('?'), 'weak');
});

// THE REGRESSION the end screen had: 66% is a real grade A on this component,
// and the old `percentage >= 80 ? strong : >= 60 ? fair` rule called it "fair".
test('a genuine multiple-choice A reads as strong', () => {
  const a = PAPER_THRESHOLDS['0625/2']!.grades.A!;
  const marks = Math.ceil(a.mean * 40);
  const r = readiness(marks, 40, 40, '0625', 2);
  assert.equal(r.grade, 'A');
  assert.equal(gradeTone(r.grade), 'strong');
  assert.ok(marks / 40 < 0.8, 'and it does so below the old 80% cut-off');
});

// 83% on a Core paper is a C, and that is the paper's limit rather than the
// student's. The app has to be able to SAY that, or the number looks broken.
test('isPaperCeiling identifies the top grade a paper can award', () => {
  const core = thresholdsFor('0625', 1);
  const ext = thresholdsFor('0625', 2);
  assert.equal(isPaperCeiling('C', core), true, 'C is the Core ceiling');
  assert.equal(isPaperCeiling('D', core), false);
  assert.equal(isPaperCeiling('A', ext), true, 'A is the Extended ceiling');
  assert.equal(isPaperCeiling('C', ext), false);
  assert.equal(isPaperCeiling('A', null), false, 'no thresholds, no claim');
});

test('a strong Core score is a C, and is flagged as the ceiling', () => {
  const r = readiness(33, 40, 40, '0625', 1);   // 82.5%
  assert.equal(r.grade, 'C');
  assert.ok(isPaperCeiling(r.grade, r.thresholds),
    'the student is at the paper limit, not falling short of an A');
  assert.ok(isTierCapped(r.thresholds), 'and that limit is the tier, not the grade scale');
});

// The bug this pair exists to prevent: an A on the Extended paper is also the
// ceiling, and telling that student to "sit the Extended paper" is nonsense.
test('a top grade on an untiered paper is not a tier cap', () => {
  const r = readiness(28, 40, 40, '0625', 2);   // 70%, an A on Extended
  assert.equal(r.grade, 'A');
  assert.ok(isPaperCeiling(r.grade, r.thresholds), 'A is the top of the scale');
  assert.equal(isTierCapped(r.thresholds), false,
    'but the paper is not capped - so no ceiling message may be shown');
});

test('readiness carries how much the boundary itself moves', () => {
  const r = readiness(28, 40, 40, '0625', 2);
  assert.ok(r.boundarySd !== null && r.boundarySd > 0,
    'a boundary averaged over many sessions has spread, and it must be reported');
});

// ------------------------------------------------------------- SS H assembly

let seq = 0;
const row = (over: Partial<PracticeRow> = {}): PracticeRow => ({
  topic_id: 't1', topic_name: 'Waves', subject_code: '0625',
  is_correct: true, option_count: 4, marks: 1,
  local_date: '2026-08-20', started_at: `2026-08-20T10:00:${String(seq++).padStart(2, '0')}Z`,
  paper_id: '0625_s24_21', paper_number: 2, question_number: 1, ...over,
});

test('readTopic orders by started_at regardless of input order', () => {
  const a = row({ is_correct: false, started_at: '2026-08-01T09:00:00Z' });
  const b = row({ is_correct: true, started_at: '2026-08-02T09:00:00Z' });
  const forwards = readTopic([a, b], '2026-08-02');
  const backwards = readTopic([b, a], '2026-08-02');
  close(forwards.mastery, backwards.mastery);
});

test('readTopic measures decay from the most recent practice', () => {
  const r = readTopic([row({ local_date: '2026-08-01' })], '2026-08-21');
  assert.equal(r.daysSincePractice, 20);
  assert.ok(r.retention < 1);
});

test('buildQueue groups by topic and ranks by score', () => {
  const rows = [
    ...Array.from({ length: 10 }, () => row({ topic_id: 'strong', is_correct: true })),
    ...Array.from({ length: 10 }, (_, i) =>
      row({ topic_id: 'mixed', topic_name: 'Mixed', is_correct: i % 2 === 0 })),
  ];
  const q = buildQueue(rows, '2026-08-20');
  assert.equal(q.length, 2);
  assert.equal(q[0]!.topicId, 'mixed', 'the learnable topic must come first');
  for (let i = 1; i < q.length; i++) {
    assert.ok(q[i - 1]!.score >= q[i]!.score, 'queue must be sorted');
  }
});

// A question tagged with two topics is ONE question. Listing it twice would
// tell the student to redo the same question two evenings running.
test('missedQuestions deduplicates a question shared by two topics', () => {
  const rows = [
    row({ topic_id: 'a', topic_name: 'A', is_correct: false, question_number: 7 }),
    row({ topic_id: 'b', topic_name: 'B', is_correct: false, question_number: 7 }),
  ];
  const missed = missedQuestions(rows, buildQueue(rows, '2026-08-20'));
  assert.equal(missed.length, 1);
  assert.equal(missed[0]!.questionNumber, 7);
});

test('missedQuestions lists only wrong answers', () => {
  const rows = [
    row({ is_correct: true, question_number: 1 }),
    row({ is_correct: false, question_number: 2 }),
  ];
  const missed = missedQuestions(rows, buildQueue(rows, '2026-08-20'));
  assert.equal(missed.length, 1);
  assert.equal(missed[0]!.questionNumber, 2);
});

// --------------------------------------------------------------------------
// SS G2. The dashboard's two figures
//
// These drive the landing page, which is the first and for most sessions the
// only page a student reads. A wrong figure here is the one they carry away.
// --------------------------------------------------------------------------

// Day 0 is 2026-08-23 and dates count backwards from it, so a test can say
// "four days ago" and not do arithmetic in its own head.
const TODAY = '2026-08-23';
function ago(days: number): string {
  const d = new Date(Date.parse(`${TODAY}T00:00:00Z`) - days * 86_400_000);
  return d.toISOString().slice(0, 10);
}
function att(over: Partial<DatedAttempt> = {}): DatedAttempt {
  return {
    local_date: TODAY, accuracy: 0.5, questions_recorded: 40,
    duration_ms: 60_000, ...over,
  };
}

test('accuracyTrend stays silent below the paper minimum', () => {
  const few = Array.from({ length: MODEL.flags.minPapersForTrend },
    (_, i) => att({ local_date: ago(i), accuracy: 0.5 }));
  assert.equal(accuracyTrend(few), null,
    'at exactly the minimum the two windows would overlap');
  assert.notEqual(accuracyTrend([...few, att({ local_date: ago(99), accuracy: 0.5 })]), null);
});

test('accuracyTrend reads the newest papers against the oldest, not the file order', () => {
  // Shuffled on purpose: the input arrives from the query in whatever order
  // the view returns, so the function must sort by date itself.
  const rising: DatedAttempt[] = [
    att({ local_date: ago(0), accuracy: 0.9 }),
    att({ local_date: ago(30), accuracy: 0.2 }),
    att({ local_date: ago(10), accuracy: 0.8 }),
    att({ local_date: ago(25), accuracy: 0.3 }),
    att({ local_date: ago(20), accuracy: 0.4 }),
    att({ local_date: ago(5), accuracy: 0.9 }),
  ];
  const up = accuracyTrend(rising);
  assert.ok(up !== null && up > 0, 'improving practice must read as improving');
  // The same six papers with the dates reversed have to read as the decline.
  const falling = rising.map(a => ({ ...a, accuracy: 1 - (a.accuracy ?? 0) }));
  const down = accuracyTrend(falling);
  assert.ok(down !== null && down < 0);
  assert.ok(Math.abs(up + down) < 1e-12, 'and by exactly the same magnitude');
});

test('accuracyTrend ignores unmarked papers rather than scoring them zero', () => {
  const marked = Array.from({ length: 6 },
    (_, i) => att({ local_date: ago(i), accuracy: 0.6 }));
  const withBlanks = [...marked, att({ local_date: ago(3), accuracy: null })];
  assert.equal(accuracyTrend(withBlanks), accuracyTrend(marked));
});

test('recentActivity compares the last seven days with the seven before', () => {
  const r = recentActivity([
    att({ local_date: ago(0) }), att({ local_date: ago(3) }), att({ local_date: ago(6) }),
    att({ local_date: ago(7) }), att({ local_date: ago(13) }),
    att({ local_date: ago(14) }),  // outside both windows entirely
  ], TODAY);
  assert.equal(r.papers.current, 3);
  assert.equal(r.papers.previous, 2);
  assert.equal(r.papers.delta, 1);
  assert.ok(r.papers.comparable);
  assert.equal(r.questions.current, 120);
  assert.equal(r.timeMs.previous, 120_000);
});

test('a first week is not "up on last week"', () => {
  const r = recentActivity([att(), att({ local_date: ago(2) })], TODAY);
  assert.equal(r.papers.current, 2);
  assert.equal(r.papers.comparable, false,
    'with no earlier window the total is a starting figure, not growth');
  assert.equal(r.accuracy.comparable, false);
});

test('an earlier week of unmarked papers is comparable on count but not on accuracy', () => {
  const r = recentActivity([
    att({ local_date: ago(1), accuracy: 0.8 }),
    att({ local_date: ago(8), accuracy: null }),
  ], TODAY);
  assert.equal(r.papers.comparable, true);
  assert.equal(r.accuracy.comparable, false,
    'a week with no marked paper has no accuracy to be up on');
});

test('recentActivity averages accuracy rather than summing it', () => {
  const r = recentActivity([
    att({ local_date: ago(1), accuracy: 0.4 }),
    att({ local_date: ago(2), accuracy: 0.6 }),
    att({ local_date: ago(8), accuracy: 0.5 }),
  ], TODAY);
  assert.equal(r.accuracy.current, 0.5);
  assert.equal(r.accuracy.previous, 0.5);
  assert.equal(r.accuracy.delta, 0);
});

test('recentActivity treats a missing count as zero, not as NaN', () => {
  const r = recentActivity([
    att({ local_date: ago(1), questions_recorded: null, duration_ms: null }),
    att({ local_date: ago(8) }),
  ], TODAY);
  assert.equal(r.questions.current, 0);
  assert.equal(r.timeMs.current, 0);
  assert.ok(Number.isFinite(r.questions.delta));
});

// --------------------------------------------------------------------------
// SS I. The IDE
// --------------------------------------------------------------------------

function sub(over: Partial<Parameters<typeof readIde>[1][number]> = {}) {
  return {
    record_id: 'r1', score: 3, max_marks: 6,
    local_date: TODAY, created_at: `${TODAY}T09:00:00Z`, ...over,
  };
}
const TOTALS = {
  attempted: 2, solved: 1, submissions: 3,
  best_marks: 9, best_marks_possible: 12,
};

test('a student who has never opened the IDE reads as nothing, not as zero skill', () => {
  const r = readIde(null, []);
  assert.equal(r.attempted, 0);
  assert.equal(r.firstTryRate, null, 'no submissions is not a 0% first-try rate');
  assert.equal(r.submissionsPerSolve, null);
  assert.equal(r.trend, null);
});

test('the headline counts come from the view, not from the capped log', () => {
  // The log here is deliberately shorter than the totals claim.
  const r = readIde(TOTALS, [sub()]);
  assert.equal(r.submissions, 3, 'the view sees every row; the log does not');
  assert.equal(r.solved, 1);
  assert.equal(r.marksAwarded, 9);
});

test('a truncated log withholds the rates rather than reporting a biased one', () => {
  // One question in the log, two attempted: the sample is the oldest work
  // only, which would understate anyone who has since improved.
  const r = readIde(TOTALS, [sub()]);
  assert.equal(r.complete, false);
  assert.equal(r.firstTryRate, null);
});

test('a first-submission solve is counted, a later one is not', () => {
  const totals = { ...TOTALS, attempted: 2, solved: 2, submissions: 3 };
  const r = readIde(totals, [
    // r1: solved immediately.
    sub({ record_id: 'r1', score: 6, max_marks: 6, created_at: `${TODAY}T09:00:00Z` }),
    // r2: missed first, solved second.
    sub({ record_id: 'r2', score: 2, max_marks: 6, created_at: `${TODAY}T10:00:00Z` }),
    sub({ record_id: 'r2', score: 6, max_marks: 6, created_at: `${TODAY}T11:00:00Z` }),
  ]);
  assert.equal(r.complete, true);
  assert.equal(r.firstTrySolves, 1);
  assert.equal(r.firstTryRate, 0.5);
  assert.equal(r.submissionsPerSolve, 1.5);
});

test('"first" means first in time, not first in the array', () => {
  // The log arrives from the query in whatever order it arrives in.
  const totals = { ...TOTALS, attempted: 1, solved: 1, submissions: 2 };
  const r = readIde(totals, [
    sub({ record_id: 'r1', score: 6, max_marks: 6, created_at: `${TODAY}T11:00:00Z` }),
    sub({ record_id: 'r1', score: 1, max_marks: 6, created_at: `${TODAY}T09:00:00Z` }),
  ]);
  assert.equal(r.firstTrySolves, 0,
    'the 1/6 was first; solving on the retry is not a first-try solve');
});

test('the IDE trend is per submission, and improving practice reads as improving', () => {
  const totals = { ...TOTALS, attempted: 8, solved: 4, submissions: 8 };
  const log = Array.from({ length: 8 }, (_, i) => sub({
    record_id: `r${i}`,
    score: i, max_marks: 7,
    local_date: ago(8 - i),
    created_at: `${ago(8 - i)}T09:00:00Z`,
  }));
  const r = readIde(totals, log);
  assert.ok(r.trend !== null && r.trend > 0);
});

test('a question worth no marks cannot drag the IDE trend to zero', () => {
  const totals = { ...TOTALS, attempted: 7, solved: 0, submissions: 7 };
  const scored = Array.from({ length: 6 }, (_, i) => sub({
    record_id: `r${i}`, score: 3, max_marks: 6,
    local_date: ago(6 - i), created_at: `${ago(6 - i)}T09:00:00Z`,
  }));
  const withUnmarkable = [...scored, sub({
    record_id: 'rx', score: 0, max_marks: 0,
    local_date: ago(3), created_at: `${ago(3)}T12:00:00Z`,
  })];
  assert.equal(readIde(totals, withUnmarkable).trend, readIde(totals, scored).trend);
});

// --------------------------------------------------------------------------
// SS G1. Behavioural flags
//
// These three moved out of v_question_flags (migration 00000000000007) and had
// no test coverage of any kind while they lived in SQL.
// --------------------------------------------------------------------------

function q(over: Partial<FlaggableQuestion> = {}): FlaggableQuestion {
  return {
    is_correct: true, confidence: 0.6,
    time_spent_ms: 60_000, median_time_ms: 60_000,
    exploration_depth: 3, eliminated_mask: 0, ...over,
  };
}

test('a guess is fast AND unworked, not merely fast', () => {
  const fastAndBlank = q({ time_spent_ms: 10_000, exploration_depth: 0, eliminated_mask: 0 });
  assert.equal(isGuess(fastAndBlank), true);
  // Fast, but the student eliminated options - that is a quick decision.
  assert.equal(isGuess({ ...fastAndBlank, eliminated_mask: 0b0010 }), false);
  // Fast, but they worked the question.
  assert.equal(isGuess({ ...fastAndBlank, exploration_depth: 5 }), false);
  // Unworked, but they sat with it - not a guess either.
  assert.equal(isGuess({ ...fastAndBlank, time_spent_ms: 59_000 }), false);
});

test('the guess threshold is relative to the paper, not to the clock', () => {
  // The same 20 seconds is a guess on a slow paper and a normal answer on a
  // fast one. A fixed number of seconds could not express that.
  assert.equal(isGuess(q({ time_spent_ms: 20_000, median_time_ms: 100_000, exploration_depth: 0 })), true);
  assert.equal(isGuess(q({ time_spent_ms: 20_000, median_time_ms: 30_000, exploration_depth: 0 })), false);
});

test('no median means no claim', () => {
  // percentile_cont returns null for an attempt with no timed questions;
  // 0.4 * null must not become 0 and flag everything as a guess.
  assert.equal(isGuess(q({ median_time_ms: 0, time_spent_ms: 1, exploration_depth: 0 })), false);
});

test('overconfidence is confident AND wrong', () => {
  assert.equal(isOverconfident(q({ confidence: 0.9, is_correct: false })), true);
  assert.equal(isOverconfident(q({ confidence: 0.9, is_correct: true })), false);
  assert.equal(isOverconfident(q({ confidence: 0.5, is_correct: false })), false);
});

test('underconfidence is unsure AND right', () => {
  assert.equal(isUnderconfident(q({ confidence: 0.2, is_correct: true })), true);
  assert.equal(isUnderconfident(q({ confidence: 0.2, is_correct: false })), false);
  assert.equal(isUnderconfident(q({ confidence: 0.8, is_correct: true })), false);
});

// The SQL these replaced was inclusive in its text and EXCLUSIVE in fact.
// question_metrics.confidence is `real`, so `confidence >= 0.7` widened it to
// 0.699999988079071 and every question sitting exactly on the boundary was
// silently never flagged - 8 overconfident and 19 underconfident out of 1,840
// rows in the local database. Comparing in TypeScript, where both sides are
// doubles, makes the rule mean what it says.
test('the thresholds are inclusive at the boundary, which the SQL was not', () => {
  assert.equal(isOverconfident(q({ confidence: MODEL.flags.overconfidentAbove, is_correct: false })), true);
  assert.equal(isUnderconfident(q({ confidence: MODEL.flags.underconfidentBelow, is_correct: true })), true);
});

test('an unmarked or unmeasured question is flagged as nothing', () => {
  // question_metrics is a left join, so confidence is null whenever the
  // metrics for that question were never computed. Null is not low confidence.
  assert.equal(isOverconfident(q({ confidence: null, is_correct: false })), false);
  assert.equal(isUnderconfident(q({ confidence: null, is_correct: true })), false);
  // And an unmarked question is not a wrong one.
  assert.equal(isOverconfident(q({ confidence: 0.9, is_correct: null })), false);
});
