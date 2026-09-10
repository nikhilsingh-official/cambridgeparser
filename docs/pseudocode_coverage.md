<!-- ====================================================================== -->
<!-- Corpus and syllabus coverage audit, measured 2026-09-10.               -->
<!-- ====================================================================== -->

# Pseudocode corpus coverage

This audit measures the committed IDE corpus, not Cambridge's complete archive.
Counts come from `public/resources/pseudocode_question_records.json`; a
“paper” is one unique `paper_code`, and a tagged question has at least one
`syllabus_tags` entry.

## Result by qualification stage

| Stage | Relevant Cambridge scope | Questions in the IDE | Topic-tagged | Assessment |
|---|---|---:|---:|---|
| IGCSE | 0478 / 0984 Paper 2 | 39 | 39 (100%) | Meaningful 0478 sample; 0984 not yet covered |
| AS Level | 9608 / 9618 Paper 2 | 176 | 176 (100%) | Strong historical Paper 2 set |
| A Level | AS Paper 2 content carried into the full A Level | 176 | 176 (100%) | Core programming covered; not A-Level-only material |
| A-Level-only | 9618 Papers 3 and 4 | 0 | 0 | Not covered |

The distinction in the last two rows matters. Cambridge's current 9618
structure makes Paper 2 worth 50% of AS Level and 25% of the full A Level, while
Papers 3 and 4 supply the A-Level-only half. Paper 2 requires pseudocode;
Paper 4 requires complete code in Java, Visual Basic, or Python. The existing
IDE is therefore useful to both AS and A Level candidates, but it must not be
described as covering the advanced half of A Level. See the official
[9618 syllabus for 2026](https://www.cambridgeinternational.org/Images/697372-2026-syllabus.pdf).

The IGCSE sample now covers 0478 Paper 2 questions from all three exam series,
including algorithms, programming, arrays, validation, and file handling. It
does not yet represent every year or the equivalent 0984 syllabus. Current 0478
Paper 2 includes algorithms and programming and ends with a 15-mark unseen
scenario requiring pseudocode or program code. See the official
[0478 syllabus for 2026–2028](https://www.cambridgeinternational.org/Images/697167-2026-2028-syllabus.pdf).

## Historical breadth inside the covered set

| Syllabus | Questions | Unique papers | Years | Exam series represented |
|---|---:|---:|---|---|
| 0478 | 39 | 20 | 2017, 2019, 2021–2025 | Feb/March, May/June, Oct/Nov |
| 9608 (legacy) | 56 | 20 | 2016–2020 | May/June, Oct/Nov |
| 9618 | 120 | 25 | 2021–2025 | May/June, Oct/Nov |
| Total | 215 | 65 | 2016–2025 | All three series represented |

All records come from components 21, 22, or 23; there are no advanced
components. The 39 canonical IGCSE records were selected from 40 source
segments across 21 source papers, with one repeated question deduplicated. The
AS/A Level set still has no February/March questions and no May/June 2022
records.

## Topic-tag coverage

- 215 of 215 questions have tags: record-level completeness is 100%.
- The corpus contains 1009 tag assignments across 32 distinct topic slugs.
- Every question has four or five tags.
- 0478 contributes 175 assignments across 22 slugs, mapped to its own Topics 7
  and 8 rather than inheriting AS/A Level section numbers.
- 9608 contributes 259 assignments across 30 slugs; 9618 contributes 575
  assignments across 30 slugs.
- The most common tags are IF selection (94), procedures (71), functions (69),
  string handling (69), variables and constants (62), 1D arrays (62),
  count-controlled loops (59), and built-in functions (58).
- Thin areas include stepwise refinement (2), error correction (2), stacks (3),
  structured English (4), bubble sort (5), flowcharts (6), CASE selection (8),
  and structure charts (8).

“100% tagged” means every included question is discoverable by topic. It does
not mean the syllabus is 100% covered: the records concentrate on algorithm and
programming topics, while 0984 and A-Level-only assessment are absent.

## Recommended expansion order

1. Fill the omitted 0478 years and variants, then add equivalent 0984 Paper 2
   questions using the same image, layout, answer-text, marking-point, and tag
   contracts as the current corpus.
2. Fill the missing 9618 May/June 2022 and Feb/March sessions before widening
   the date range; these are bounded holes in an otherwise continuous set.
3. Decide whether the product should support Paper 4 source-code tasks. If so,
   treat them as a separate answer mode rather than labelling them pseudocode.
4. Add question-level coverage targets for the thin algorithm tags, then audit
   against syllabus learning objectives—not only the set of tags that happens
   to occur in existing questions.
