<!--
-->

# Solver golden corpus

This corpus tests the MCQ solver at its highest-risk boundary: Cambridge PDF
bytes → PDF.js text and geometry → question segmentation → answer-option
association, plus the deployed `fetch-pdf` mark-scheme extractor.

It contains one reviewed paper for each of the 19 paper families currently
listed by the solver. The selection spans 2016–2025, February/March,
May/June and October/November series, IGCSE, O Level and AS/A Level, Core and
Extended papers, and old and current PDF layouts.

## What is committed

[`manifest.ts`](../../../scripts/solver-corpus/manifest.ts) is the golden set.
For every paper it records:

- source filenames, byte sizes, page counts and SHA-256 hashes;
- expected question count and questions per page;
- the complete literal answer key;
- selected option-marker bounding boxes at PDF viewport scale 1;
- selected option-to-text associations; and
- explicitly reviewed failures in the current parser.

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
- each current failure was reproduced through the real application pipeline
  before being classified as known.

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

The initial reviewed baseline is 19 papers and 778 checks: 13 known failing
checks, zero unexpected failures and zero unexpected passes. Known failures
are visible audit results, not passes.

## Current paper set

| Paper | Family | Why it is present |
| --- | --- | --- |
| `0455_s16_11` | 0455/1 | old 30-question economics layout |
| `0610_w16_11` | 0610/1 | old Core biology layout |
| `0610_s25_22` | 0610/2 | current Extended biology layout |
| `0620_m18_12` | 0620/1 | stacked-fraction option failure |
| `0620_w24_23` | 0620/2 | current dense chemistry tables |
| `0625_s18_11` | 0625/1 | Core physics diagrams and graphs |
| `0625_s24_22` | 0625/2 | current Extended physics layout |
| `0653_w19_11` | 0653/1 | duplicate diagram-marker failure |
| `0653_m25_22` | 0653/2 | current mixed-science layout |
| `0654_w18_11` | 0654/1 | older co-ordinated science layout |
| `0654_s25_23` | 0654/2 | current co-ordinated science layout |
| `9700_w16_13` | 9700/1 | old marker-segmentation regression |
| `9701_m25_12` | 9701/1 | spatial option-order regression |
| `9702_s24_12` | 9702/1 | two-cover-page A-Level layout |
| `9708_s25_13` | 9708/1 | option-text association regression |
| `5090_s16_11` | 5090/1 | old O-Level mark-scheme format |
| `5070_w25_12` | 5070/1 | current O-Level chemistry layout |
| `5054_w18_12` | 5054/1 | table-label option-count regression |
| `2281_w25_13` | 2281/1 | inline-label and association regressions |

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
