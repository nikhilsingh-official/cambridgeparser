<!--
-->

# Solver golden corpus

This corpus tests the MCQ solver at its highest-risk boundary: Cambridge PDF
bytes → PDF.js text and geometry → question segmentation → answer-option
association, plus the deployed `fetch-pdf` mark-scheme extractor.

It contains one reviewed paper for each of the 19 paper families currently
listed by the solver. The selection spans 2017–2025, February/March,
May/June and October/November series, IGCSE, O Level and AS/A Level, Core and
Extended papers, and multiple supported PDF layouts. Papers from 2016 and
earlier are outside the product boundary and are not offered by the catalogue.

## What is committed

[`manifest.ts`](../../../scripts/solver-corpus/manifest.ts) is the golden set.
For every paper it records:

- source filenames, byte sizes, page counts and SHA-256 hashes;
- expected question count and questions per page;
- the complete literal answer key;
- selected option-marker bounding boxes at PDF viewport scale 1;
- selected option-to-text associations; and
- explicitly reviewed failures in the current parser, if any are introduced.

The Cambridge source PDFs are not committed. They are downloaded into the
ignored `cache/` directory and accepted only when their byte count and SHA-256
match the manifest.

## Basis of truth

The expected results were established independently of the application parser:

- question starts and page placement were checked page by page using Poppler's
  layout-preserving text extraction;
- answer strings were transcribed from the published Cambridge mark schemes;
- selected coordinates were checked at scale 1 against rendered source pages;
- selected option text was transcribed from the rendered question papers; and
- every parser failure discovered while establishing the corpus was reproduced
  through the real application pipeline and visually reviewed before its fix.

Do not generate expected values by serialising the parser output. That would
turn regressions into the new expected result.

## Run the audit

From the repository root:

```sh
node --experimental-strip-types scripts/solver-corpus/fetch.ts
npm ci --prefix supabase/functions/fetch-pdf
node --experimental-strip-types scripts/solver-corpus/validate.ts
```

The fetcher is deliberately serial and waits between network requests. It is
safe to rerun: already verified PDFs are read from the cache.

The validator loads the actual modules under `src/lib/pdf/` through Vite and
the same answer-key implementation used by the Supabase Edge Function. It exits
non-zero for:

- a check that fails without an explicit known-failure declaration; or
- a known failure that starts passing before its expectation is reviewed and
  its declaration is removed.

The current reviewed baseline is 19 papers and 819 checks: all checks pass,
with zero known failures, unexpected failures or unexpected passes. If a future
limitation must be recorded temporarily, it remains a visible audit result and
is never counted as a pass.

Non-linear formula, graph and horizontal-table choices are a deliberate UI
boundary: when PDF draw order cannot prove which fragments belong to which
answer, the solver attaches each action to the independently verified A–D
marker instead of guessing a larger text region. Those label-only choices use
a 24 × 18 PDF-point click target. The geometry probes verify the source marker
identity and coordinates; they do not claim a formula-fragment association that
the parser does not make.

## Current paper set

| Paper | Family | Why it is present |
| --- | --- | --- |
| `0455_w25_12` | 0455/1 | current 30-question economics layout |
| `0610_w17_11` | 0610/1 | earliest supported Core biology layout |
| `0610_s25_22` | 0610/2 | current Extended biology layout |
| `0620_m18_12` | 0620/1 | stacked-fraction option failure |
| `0620_w24_23` | 0620/2 | current dense chemistry tables |
| `0625_s18_11` | 0625/1 | Core physics diagrams and graphs |
| `0625_s24_22` | 0625/2 | current Extended physics layout |
| `0653_w19_11` | 0653/1 | duplicate diagram-marker failure |
| `0653_m25_22` | 0653/2 | current mixed-science layout |
| `0654_w18_11` | 0654/1 | older co-ordinated science layout |
| `0654_s25_23` | 0654/2 | current co-ordinated science layout |
| `9700_w25_13` | 9700/1 | current A-Level biology layout |
| `9701_m25_12` | 9701/1 | spatial option labels |
| `9702_s24_12` | 9702/1 | two-cover-page A-Level layout |
| `9708_s25_13` | 9708/1 | vertical option-text association |
| `5090_s25_11` | 5090/1 | current O-Level biology layout |
| `5070_w25_12` | 5070/1 | current O-Level chemistry layout |
| `5054_w18_12` | 5054/1 | table-column option labels |
| `2281_w25_13` | 2281/1 | inline labels and table options |

## Manually reviewed failures

Each failure was inspected on the rendered source page and against PDF.js text
items before changing the parser.

| Paper / question | Observed failure | Root cause and outcome |
| --- | --- | --- |
| `0620_m18_12` Q8 | One stacked-fraction choice was detected instead of four | The first candidate font contained one A–D glyph and short-circuited font detection. All candidate fonts are now compared by distinct label coverage; the verified labels use enlarged label-only targets. |
| `0653_w19_11` Q36 | Five choices appeared because B was repeated | PDF.js exposed the same drawn B twice at identical coordinates. Exact-coordinate duplicates are now collapsed. |
| `9701_m25_12` Q1 | Spatial graph labels arrived as A, C, B, D | Content-stream order did not match semantic order. A complete spatial quartet is now exposed as A–D while retaining its source coordinates. |
| `9708_s25_13` Q1 | Text was attached to the wrong option | The PDF drew prose before its visible label. Association now follows visual line and x order. |
| `5054_w18_12` Q2 | Eight A–D-like markers were found in one table | Table content and answer headers shared the marker font. Complete quartets are ranked by alignment and spread; the verified header quartet uses enlarged label-only targets. |
| `2281_w25_13` Q1 | Inline A/B/C/D prose competed with the real answer labels | The parser accepted every letter in stream order. It now selects the geometrically plausible complete quartet and preserves the four answer rows. |
| `2281_w25_13` Q13 and Q24 | The following question's text leaked across each boundary | PDF draw indices were treated as reading order. Questions are now segmented between visible question-number y coordinates. |
| `2281_w25_13` Q14 and Q25 | Correcting the boundary exposed false marker groups in their tables | The same quartet ranking rejects the inline/table lettering without paper-specific exceptions; ordinary vertical table rows retain their text. |

## Extending or changing the corpus

1. Choose a paper because it adds a layout, year, question type or reproduced
   failure not already covered.
2. Fetch the question paper and mark scheme from the recorded source.
3. Record source hashes before examining parser output.
4. Establish question/page counts, answers, probes and coordinates using the
   independent review methods above.
5. Add the manifest entry and run its contract test.
6. Run the full validator. Investigate every unexpected result before changing
   either code or expectations.
7. If a parser fix resolves a known failure, visually review the affected
   question, remove that declaration, and rerun the entire corpus.

Source publishers can replace a PDF without changing its URL. A checksum
mismatch must be reviewed as a source change; never silently update the hash.
