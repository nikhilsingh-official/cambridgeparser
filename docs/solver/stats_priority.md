<!-- ==========================================================================
     Documentation only. Fourth in the series: database_design.md specifies what
     is stored, future_work.md tracks what is missing, stats_page_design.md
     specifies how stored data becomes charts, and this one ranks which of
     those charts is worth the student's attention — and therefore what order
     the page should be in.
     ========================================================================== -->

# Stats — what matters to a student, in order

`stats_page_design.md` answers "what can we draw". It never asked **"which of
these does a student actually act on"**, and the page order today is an artefact
of the order things got built, not of value.

This document ranks every stat the schema can support, grounded in published
evidence rather than taste, and says what the page order should be as a result.

---

## 0. The evidence, and its limits

### 0.1 The one ranked dataset that exists

**Schumacher & Ifenthaler (2016), *Features Students Really Expect from
Learning Analytics*** — 20 students interviewed, then **N = 216** rating **15
dashboard features** on two 5-point scales: *would I use this* and *would this
help me learn*. It is the closest thing in the literature to a database of
student wants, and it is open access.

Their means, sorted by the **learning** scale (the one we care about):

| # | Feature | Learning | Would use |
|---|---|---|---|
| 1 | Prompts for **self-assessment** | **3.73** | 4.07 |
| 2 | **Recommendations** for completing the course | **3.70** | 3.98 |
| 3 | **Timeline: current status against my objective** | **3.63** | 3.78 |
| 4 | **Repetition of learning content** | **3.57** | **4.12** |
| 5 | Further learning recommendations | 3.45 | 3.69 |
| 6 | Feedback on assignments | 3.38 | 4.07 |
| 7 | Integration of personal schedule | 3.23 | 3.50 |
| 8 | Suggested learning partners | 3.13 | 3.30 |
| 9 | Reminders | 3.08 | **4.20** |
| 10 | **Time spent online** | **2.99** | 3.13 |
| 11 | Newsfeed | 2.80 | 3.42 |
| 12 | Term scheduler | 2.79 | 3.67 |
| 13 | Rating scales for material | 2.79 | 3.31 |
| 14 | **Comparison with fellow students** | **2.60** | 2.49 |
| 15 | **Time needed to read / complete a task** | **2.44** | **2.32** |

Two findings land directly on our page:

- **Time-on-task is the least valued thing on the list.** Both time metrics sit
  at the bottom of both scales, and "time needed to complete a task" is *last on
  both*. Our card strip currently leads with six time metrics and we devote an
  entire page section to them.
- **Peer comparison is second-worst**, and the interviews found it actively
  divisive — some students found it motivating, others demotivating, and the
  authors recommend it be opt-in only. We do not have it. **Do not build it.**

What students *do* want clusters tightly: tell me what I don't know, tell me
what to do about it, and let me redo it.

The qualitative half is even more on the nose for an exam-practice app:

> the assessment conditions should be the same as during exams regarding working
> time and task difficulty … the feedback should be divided into subject areas
> enabling students to assess their need for improvement

That is a description of this product, and of a topic breakdown specifically.

### 0.2 What actually raises exam marks

**Dunlosky et al. (2013)** reviewed 10 study techniques and rated their utility.
Exactly two earned **high**: **practice testing** and **distributed practice**.
Summarising, highlighting and rereading — what most students actually do — all
rated **low**.

Both winners are things this app can drive rather than merely display. A stat
that ends in "redo these twelve questions, spaced out" is acting on the two
highest-utility findings in the field; a stat that ends in "you studied for 34
hours" is not.

### 0.3 Awareness is not the goal

**Jivet et al. (2020)** found dashboard sense-making rests on three constructs —
**reference frames**, **support for action**, and **transparency of design** —
and that only ~17% of dashboards offer any decision support at all:

> Checking a learning dashboard regularly without making any changes in your
> learning behaviour will not lead to better outcomes.

On reference frames: comparing a student against *their own goal* works for
mastery-oriented learners; comparing against *peers* only suits
performance-oriented ones and backfires for the rest. A grade target is the
right frame for us. A leaderboard is not.

### 0.4 Which topics to practise is a solved question

**Metcalfe & Kornell's region of proximal learning** says effective learners
first *drop what is already mastered*, then work the **moderately difficult**
material — not the hardest. Time spent on items far beyond reach is close to
wasted, and time on mastered items entirely so.

This matters for the "easy topics / hard topics" split: **the useful cut is
three ways, not two.**

| Band | Signal | What to tell the student |
|---|---|---|
| **Mastered** | high accuracy, enough evidence, stable | stop practising this — you are spending marks-per-hour badly |
| **Proximal** | middling accuracy, or improving | **practise here.** This is where marks are cheapest |
| **Not yet learnable** | very low accuracy, no upward trend | practice will not fix this — it needs teaching first |

A two-way easy/hard split sends the student at their worst topic, which is often
the third band and the worst use of their time.

### 0.5 Calibration is worth more than it looks

Students **systematically overpredict** their exam performance, the lowest
performers overpredict most, and — the important part — **this does not
self-correct with experience**. One study found overconfidence undiminished
after *thirteen* class exams. What does fix it is explicit feedback on the
judgement itself.

Our behavioural confidence metric is exactly that feedback, and it is a thing a
student cannot get from a past paper and a mark scheme. It is the most
defensible original metric on the page.

### 0.6 Where this evidence is thin — read before trusting the ranking

- Schumacher & Ifenthaler is **higher-ed, German, 2016, LMS-context**, N=216.
  Our users are IGCSE/A-Level students grinding past papers. The direction of
  the findings should transfer; the exact means should not be over-read.
- Dunlosky ranks **study techniques**, not dashboard features. Applying it to
  "which stat to show" is my inference, not their claim.
- Nobody has run this study on an exam-practice tool. Treat the ranking as a
  strong prior to be replaced by our own usage data, not as settled.
- Our own confidence/guess thresholds are **picked, not measured**
  (`roadmap.md` B6). Anything built on them inherits that.

---

## 1. The ranking

Scored on three axes: **evidence** (does the literature back it), **actionable**
(does it end in something to do), **feasible** (can our schema compute it
today). Ordered by value to the student.

### Tier 1 — decides what the student does next

| # | Stat | Status | Why it ranks here |
|---|---|---|---|
| 1 | **Revision queue** — ranked "practise this next" list, from weak-but-evidenced topics, weighted by staleness | **built** — `NextSteps-Overall.vue` | Hits #1, #2, #4 and #5 of the wants list at once, and is the only feature that operationalises both of Dunlosky's high-utility techniques. Nothing else on this page tells a student what to *do* |
| 2 | **Topic mastery, three-band** (mastered / proximal / not-yet) | **built** — `model.ts` §D, coloured in `Topics-Overall.vue` | §0.1's exact request ("feedback divided into subject areas"), sharpened by §0.4. The banding is a ~20-line change to work already landed |
| 3 | **Wrong-answer set** — every question missed, ranked and deep-linked | **built** — regrouping them into a generated paper is the remaining half | "Repetition of learning content" scored highest of all on willingness (4.12). It is literally practice testing, Dunlosky's #1 |
| 4 | **Exam readiness / predicted grade** against grade thresholds | **built** — on Cambridge's own published thresholds, scraped and averaged | The goal reference frame from §0.3 and #3 on the wants list. Converts an abstract percentage into the number the student actually cares about |
| 5 | **Topic decay** — what you were good at and haven't touched in N weeks | **built** — `model.ts` §C, the "fading" term of the queue | Distributed practice, Dunlosky's other high-utility technique. Cheap: `max(local_date)` per topic |

### Tier 2 — corrects *how* they study

| # | Stat | Status | Why |
|---|---|---|---|
| 6 | **Calibration** — behavioural confidence vs accuracy | **built** | §0.5. Doesn't self-correct without exactly this feedback |
| 7 | **Overconfident questions** — sure and wrong | **built** | The misconceptions a student will never think to revise, because they don't know they're wrong |
| 8 | **Answer-change quality** — first instinct vs second | **built** | Answers a question every student asks, with their own data. Immediately actionable |
| 9 | **Guess rate and guess accuracy** | **built** | Separates "didn't know" from "knew and slipped" — different fixes |
| 10 | **Elimination precision** — how often you rule out the right answer | **not built** | Technique feedback unavailable anywhere else. `eliminated_mask` × `correct_option` |
| 11 | **Pacing / fatigue curve** through a paper | **not built** | Exam-technique finding, needs `attempt_events` ordering (we have it) |

### Tier 3 — orientation. Keep, but stop leading with it

| # | Stat | Status | Why demoted |
|---|---|---|---|
| 12 | Accuracy trend over time | **built** | Genuine progress signal, but backward-looking: tells you *that* you improved, never what to do next |
| 13 | Marks awarded / available, papers, questions | **built** | Orientation. Necessary context, not a finding |
| 14 | Subject split | **built** | Shows where effort went. One tile's worth of insight |
| 15 | Streak, calendar heatmap | **built** | Motivational, and honestly the weakest-evidenced things we show — habit metrics are popular with builders and mid-table with students |

### Tier 4 — demote hard, or don't build

| # | Stat | Status | Verdict |
|---|---|---|---|
| 16 | Total time, time per paper, peak hour, fastest/longest paper | **built — six of these** | §0.1 ranks time metrics **last and second-last**. They are near-free to compute, which is why every dashboard has them, and that is not a reason. Cut to one, move below the fold |
| 17 | Time since last paper | **built** | Only earns its place attached to a nudge |
| 18 | **Peer comparison / leaderboards** | not built | **Do not build.** Second-worst rated, actively demotivating for the students who most need help |
| 19 | `metrics_version`, `stable_elimination_ratio`, `exploration_breadth` | internal | Already correctly excluded — provenance and intermediate inputs, not findings |

### Needs more than one user

| Stat | Note |
|---|---|
| **Item difficulty — hard for you vs hard for everyone** | Genuinely valuable: it stops a student concluding they're weak at a topic when the question was simply brutal. Computable from `question_attempts` across users, and it is **not** peer comparison — no ranking, no other student is visible — so §0.1's objection does not apply. Blocked only on having a cohort |

---

## 1.1 What the build changed about this ranking

Two things worth recording, because both were discovered by measuring rather
than by reasoning.

**Bayesian Knowledge Tracing did not survive contact with the data.** It was the
obvious choice for mastery, was implemented and tested, and then put 43 of 51
topics in "mastered" at accuracies between 61% and 73%. The cause is grain: BKT
models one skill with a rare slip, and needs slip capped near 0.10 to stay
identifiable (Baker et al. 2008). Measured on our own rows the **median topic
error rate is 0.30, and 48 of 49 topics with enough evidence exceed the
ceiling** — a syllabus topic is dozens of skills, so a 30% error rate is not
slipping, it is not knowing a third of the topic. Replaced with exponentially
recency-weighted accuracy, which keeps the order-sensitivity that made BKT
attractive and claims nothing about hidden states. `model.ts` §B carries the
full note.

**The grade thresholds were invented, and badly wrong.** The model shipped
against "typical" percentages — A at 80%, C at 60% — because no real data was to
hand. `scripts/gt/build.py` now scrapes Cambridge's own published
grade-threshold documents: **406 documents, 4,612 component rows**, averaged per
paper into `src/constants/gradeThresholds.ts`.

Real multiple-choice thresholds run far lower than intuition suggests, because
there is no partial credit and chance contributes 25%:

| Paper | Grade A | Grade C | Grade E |
|---|---|---|---|
| 0625/2 Physics Extended | **66.1%** ±5.8 | 50.5% ±5.0 | 38.8% ±3.1 |
| 0620/2 Chemistry Extended | 68.3% ±4.9 | 48.2% ±4.8 | 36.6% ±3.2 |
| 9702/1 Physics A Level | 71.5% ±5.5 | 53.1% ±5.4 | 38.0% ±5.2 |
| 5070/1 Chemistry O Level | 68.2% ±6.4 | 42.1% ±4.2 | 31.9% ±3.1 |
| 0625/1 Physics Core | **— (cannot award)** | 57.2% ±4.8 | 44.7% ±3.3 |

The invented table was costing a student roughly two grades. Three structural
facts came out of the real documents and are now in the model:

- **Core-tier papers cannot award above a C.** Those cells are an en dash. The
  mastery bar is therefore the top grade *that paper* awards, not a constant.
- **There is no A\*** at component level; the documents say so explicitly.
- Readiness had to move from per-*subject* to per-*paper*. Pooling a student's
  Core and Extended attempts graded both against whichever scale won.

Fixing the bar also fixed the banding: against the same dev seed, "mastered"
went from **0 topics to 8**, and all four bands now carry signal where before
46 of 51 topics sat in one.

**Then the average turned out to be a second-best answer.** Averaging was only
ever a stand-in for a number we did not have — but a past paper names its own
session and variant, so for most papers we *do* have it. `SESSION_THRESHOLDS`
now ships the boundary Cambridge published for each exact paper, keyed by the
app's own schema (`0625_s24_21`), and `model.ts` prefers it.

How much it matters, measured across every possible mark on all 1,195 covered
papers — 47,855 gradings:

| | |
|---|---|
| Average agrees with the paper's own boundary | 81.2% |
| Differs by one grade | 15.5% |
| Differs by two grades or more | 3.3% |

The spread lives *within* single sessions as much as between them. IGCSE
Physics Extended, June 2024: grade A was **24, 25 and 27 marks** on variants
21, 22 and 23. A student on 25/40 sat an A paper or a B paper depending which
one they opened, and the mean calls all three a B.

Coverage is 86% of the catalogue and cannot be complete — **the June 2020
series was cancelled**, so no threshold was ever set for it, and a handful of
other documents are missing from the mirror. Those fall back to the average,
and the UI says which of the two it used rather than presenting both as the
same claim.

## 2. What the page order should be

Current order is Progress → Topics → Engagement → Focus. That puts the
best-evidenced section third and a section built entirely on the
worst-rated metric second.

Built, as of this change — the page now renders in this order:

1. **Next steps** — revision queue, readiness, wrong-answer set. The one
   section that ends in a verb
2. **Topics** — three-band mastery
3. **Progress** — accuracy trend and marks
4. **Focus** — calibration, overconfidence, answer changes
5. **Engagement** — streak and calendar, **last**

The DOM order matches, not just the grid rows: placing sections by `grid-row`
alone would leave the tab order and every screen reader disagreeing with what
the page looks like.

**Still to do here:** the card strip is eleven cards, six of them time metrics.
It should be cut to accuracy, papers, streak, weakest topic and readiness.

---

## 3. Cheapest first

Ranked by value ÷ effort, for whatever gets picked up next:

1. ~~Three-band topic labels~~ — **done**
2. ~~Topic decay~~ — **done**
3. **Trim the time metrics** — deleting cards, not building them. Still open
4. ~~Revision queue~~ — **done**
5. **Wrong-answer re-practice** — the list is built; generating a paper from an
   arbitrary question set still needs a solver entry point
6. ~~Real grade thresholds~~ — **done**. `scripts/gt/build.py`, re-runnable

---

## Sources

- Schumacher, C. & Ifenthaler, D. (2016). *Features Students Really Expect from Learning Analytics*. CELDA 2016. <https://files.eric.ed.gov/fulltext/ED571398.pdf>
- Dunlosky, J. et al. (2013). *Improving Students' Learning With Effective Learning Techniques*. Psychological Science in the Public Interest. <https://journals.sagepub.com/doi/abs/10.1177/1529100612453266>
- Jivet, I. et al. (2020). *From students with love: learner goals, self-regulated learning and sense-making of learning analytics*. The Internet and Higher Education. Summary: <https://www.solaresearch.org/2020/10/designing-dashboards-to-help-students-take-action/>
- Schwendimann, B. et al. (2017). *Perceiving Learning at a Glance: A Systematic Literature Review of Learning Dashboard Research*. IEEE TLT. <https://eric.ed.gov/?id=EJ1141028>
- Metcalfe, J. & Kornell, N. (2005). *A Region of Proximal Learning model of study time allocation*. JML. <http://www.columbia.edu/cu/psychology/metcalfe/PDFs/Metcalfe%20Kornell%202005.pdf>
- Metcalfe, J. (2009). *Metacognitive Judgments and Control of Study*. <http://www.columbia.edu/cu/psychology/metcalfe/PDFs/Metcalfe2009CD.pdf>
- Foster, N. et al. (2023). *Low-Performing Students Confidently Overpredict Their Grade Performance throughout the Semester*. J. Intelligence. <https://doi.org/10.3390/jintelligence11100188>
- Corbett, A.T. & Anderson, J.R. (1995). *Knowledge tracing: Modeling the acquisition of procedural knowledge*. UMUAI 4(4), 253-278.
- Baker, R.S.J.d., Corbett, A.T. & Aleven, V. (2008). *More Accurate Student Modeling through Contextual Estimation of Slip and Guess Probabilities in Bayesian Knowledge Tracing*. ITS 2008.
- Settles, B. & Meeder, B. (2016). *A Trainable Spaced Repetition Model for Language Learning*. ACL 2016. <https://research.duolingo.com/papers/settles.acl16.pdf>
- Pavlik, P.I., Cen, H. & Koedinger, K.R. (2009). *Performance Factors Analysis - A New Alternative to Knowledge Tracing*. AIED 2009.
- Wilson, E.B. (1927). *Probable Inference, the Law of Succession, and Statistical Inference*. JASA 22(158), 209-212.
- Cambridge International grade threshold tables. <https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-upper-secondary/cambridge-igcse/grade-threshold-tables/>
- Valle, N. et al. (2021). *Staying on target: a systematic literature review on learner-facing learning analytics dashboards*. BJET. <https://bera-journals.onlinelibrary.wiley.com/doi/abs/10.1111/bjet.13089>
