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
| IGCSE | 0478 / 0984 Paper 2 | 205 | 205 (100%) | Broad 0478 coverage for 2016–2025; 0984 not yet covered |
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

The IGCSE set now covers every valid 0478 Paper 2 paper in the local 2016–2025
archive across all three exam series, including algorithms, programming,
arrays, validation, error correction, and file handling. It does not cover the
equivalent 0984 syllabus. Current 0478 Paper 2 includes algorithms and
programming and ends with a 15-mark unseen scenario requiring pseudocode or
program code. See the official
[0478 syllabus for 2026–2028](https://www.cambridgeinternational.org/Images/697167-2026-2028-syllabus.pdf).

## Historical breadth inside the covered set

| Syllabus | Canonical questions | Source papers audited | Years | Exam series represented |
|---|---:|---:|---|---|
| 0478 | 205 | 69 | 2016–2025 | Feb/March, May/June, Oct/Nov |
| 9608 (legacy) | 56 | 20 | 2016–2020 | May/June, Oct/Nov |
| 9618 | 120 | 25 | 2021–2025 | May/June, Oct/Nov |
| Total | 381 | 114 | 2016–2025 | All three series represented |

All records come from components 21, 22, or 23; there are no advanced
components. The selector found 216 IGCSE prompts across all 69 valid source
papers. One officially withdrawn question was discarded, and 10 verbatim
duplicates were merged, leaving 205 canonical records. Those duplicates make
four papers disappear as primary `paper_code` values, but their source codes
remain in trusted duplicate provenance. The AS/A Level set still has no
February/March questions and no May/June 2022 records.

## Topic-tag coverage

- 381 of 381 questions have tags: record-level completeness is 100%.
- The corpus contains 1839 tag assignments across 32 distinct topic slugs.
- Every IGCSE question has four or five tags.
- 0478 contributes 1005 assignments across 23 slugs, mapped to its own Topics 7
  and 8 rather than inheriting AS/A Level section numbers.
- 9608 contributes 259 assignments across 30 slugs; 9618 contributes 575
  assignments across 30 slugs.
- The most common tags are IF selection (174), count-controlled loops (144),
  1D arrays (139), input/output (111), post-condition loops (99), and operators
  and expressions (93).
- Thin areas include stepwise refinement (2), stacks (3), structured English
  (4), identifier tables (4), flowcharts (6), structure charts (8), and bubble
  sort (9). Error-correction coverage is no longer thin: it has 43 records.

“100% tagged” means every included question is discoverable by topic. It does
not mean the syllabus is 100% covered: the records concentrate on algorithm and
programming topics, while 0984 and A-Level-only assessment are absent.

## Recommended expansion order

1. Add equivalent 0984 Paper 2 questions using the same image, layout,
   answer-text, marking-point, and tag contracts as the current 0478 corpus.
2. Fill the missing 9618 May/June 2022 and Feb/March sessions before widening
   the date range; these are bounded holes in an otherwise continuous set.
3. Decide whether the product should support Paper 4 source-code tasks. If so,
   treat them as a separate answer mode rather than labelling them pseudocode.
4. Add question-level coverage targets for the thin algorithm tags, then audit
   against syllabus learning objectives—not only the set of tags that happens
   to occur in existing questions.
