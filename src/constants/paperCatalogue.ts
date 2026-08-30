// ==========================================================================
//
// The set of papers the Paper Browser is allowed to offer.
//
// WHY THIS FILE EXISTS
// There is no catalogue table. `supabase/functions/fetch-pdf` takes a schema
// like '0620_s24_12' and pulls that PDF from PapaCambridge on demand, so the
// space of "papers that exist" is a naming convention, not a list we hold. The
// browser therefore GENERATES its grid from the convention below rather than
// querying anything.
//
// WHY IT IS RESTRICTED TO MULTIPLE-CHOICE PAPERS
// The solver's whole pipeline assumes MCQs: lib/pdf/getOptions() looks for A-D
// option boxes to build the answer buttons, and the mark-scheme parser in
// fetch-pdf reads a Question/Answer/Marks table whose answer cells are single
// letters. Point it at, say, 0478 Paper 1 (structured written answers) and it
// loads a paper with no answerable questions. The old browser's grid was a
// mock and happily showed 32 subjects, most of which have no MCQ paper at all;
// offering them would mean most cards were broken links.
//
// TO ADD A SUBJECT: append to SOLVABLE_PAPERS. That is the only edit needed -
// the grid, the filters and the option lists are all derived from it.
// ==========================================================================

import { Qualification, ExamSeries } from '@/lib/types/enums';
import { codeToBg, codeToIcon } from './codeMaps';

/**
 * One multiple-choice paper of one syllabus, across all years.
 *
 * `variants` is per-series because the Feb/March series (India) is only ever
 * sat as variant 2 - '0620_m24_12', never '..._11' or '..._13'. Generating
 * m/1 and m/3 cards would put dead links in the grid.
 */
export interface SolvablePaper {
  code: string;
  subject: string;
  qualification: Qualification;
  /** The leading digit of the paper field: 1 in '..._12'. */
  paperNumber: number;
  /** Shown on the card, above the subject name. */
  label: string;
  series: ExamSeries[];
  /** Variants offered, keyed by series. */
  variantsBySeries: Partial<Record<ExamSeries, number[]>>;
}

const IGCSE = Qualification.IGCSE;
const OLEVEL = Qualification.OLevel;
const ALEVEL = Qualification.ASALevel;

/** s/w are sat as variants 1-3; the Feb/March series is variant 2 only. */
const FULL_VARIANTS: Partial<Record<ExamSeries, number[]>> = {
  m: [2],
  s: [1, 2, 3],
  w: [1, 2, 3],
};

/**
 * O Level syllabuses in this list are not offered in the Feb/March series, so
 * they get s/w only.
 */
const SW_VARIANTS: Partial<Record<ExamSeries, number[]>> = {
  s: [1, 2],
  w: [1, 2],
};

/** O Level Economics uses a different pair of zones in each main series. */
const oLevelEconomicsVariants: Partial<Record<ExamSeries, number[]>> = {
  s: [1, 2],
  w: [2, 3],
};

const ALL_SERIES: ExamSeries[] = ['m', 's', 'w'];
const SW_SERIES: ExamSeries[] = ['s', 'w'];

export const SOLVABLE_PAPERS: SolvablePaper[] = [
  // ---- IGCSE sciences: Paper 1 core MCQ, Paper 2 extended MCQ ----
  { code: '0610', subject: 'Biology',   qualification: IGCSE, paperNumber: 1, label: 'Paper 1: Multiple Choice (Core)',     series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0610', subject: 'Biology',   qualification: IGCSE, paperNumber: 2, label: 'Paper 2: Multiple Choice (Extended)', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0620', subject: 'Chemistry', qualification: IGCSE, paperNumber: 1, label: 'Paper 1: Multiple Choice (Core)',     series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0620', subject: 'Chemistry', qualification: IGCSE, paperNumber: 2, label: 'Paper 2: Multiple Choice (Extended)', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0625', subject: 'Physics',   qualification: IGCSE, paperNumber: 1, label: 'Paper 1: Multiple Choice (Core)',     series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0625', subject: 'Physics',   qualification: IGCSE, paperNumber: 2, label: 'Paper 2: Multiple Choice (Extended)', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0653', subject: 'Combined Science',       qualification: IGCSE, paperNumber: 1, label: 'Paper 1: Multiple Choice (Core)',     series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0653', subject: 'Combined Science',       qualification: IGCSE, paperNumber: 2, label: 'Paper 2: Multiple Choice (Extended)', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0654', subject: 'Co-ordinated Sciences',  qualification: IGCSE, paperNumber: 1, label: 'Paper 1: Multiple Choice (Core)',     series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '0654', subject: 'Co-ordinated Sciences',  qualification: IGCSE, paperNumber: 2, label: 'Paper 2: Multiple Choice (Extended)', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },

  // ---- IGCSE Economics: Paper 1 only ----
  { code: '0455', subject: 'Economics', qualification: IGCSE, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },

  // ---- AS/A Level: Paper 1 is the MCQ paper in each of these ----
  { code: '9700', subject: 'Biology',   qualification: ALEVEL, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '9701', subject: 'Chemistry', qualification: ALEVEL, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '9702', subject: 'Physics',   qualification: ALEVEL, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },
  { code: '9708', subject: 'Economics', qualification: ALEVEL, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: ALL_SERIES, variantsBySeries: FULL_VARIANTS },

  // ---- O Level ----
  { code: '5090', subject: 'Biology',   qualification: OLEVEL, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: SW_SERIES, variantsBySeries: SW_VARIANTS },
  { code: '5070', subject: 'Chemistry', qualification: OLEVEL, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: SW_SERIES, variantsBySeries: SW_VARIANTS },
  { code: '5054', subject: 'Physics',   qualification: OLEVEL, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: SW_SERIES, variantsBySeries: SW_VARIANTS },
  { code: '2281', subject: 'Economics', qualification: OLEVEL, paperNumber: 1, label: 'Paper 1: Multiple Choice', series: SW_SERIES, variantsBySeries: oLevelEconomicsVariants },
];

/**
 * Years offered, newest first.
 *
 * The lower bound is a product support boundary: 2016 and earlier mark schemes
 * use table layouts the answer-key extractor does not support. The upper bound
 * is the last series whose papers are public. Bump LATEST_YEAR when a new
 * series is released - nothing else needs to change.
 */
export const LATEST_YEAR = 2026;
const EARLIEST_YEAR = 2017;

/**
 * Sittings that cannot currently be offered.
 *
 * Cambridge cancelled the June 2020 series worldwide, so no question
 * paper, mark scheme or grade threshold was ever published for it. The
 * catalogue generates a card for every (paper x year x series x variant)
 * combination, which meant 57 of its 1,290 cards - 4.4% - opened a paper that
 * does not exist.
 *
 * VERIFIED, NOT ASSUMED. Across the 406 threshold documents scraped by
 * scripts/gt/build.py: June 2020 has 0 papers, November 2020 has 53, and
 * February/March 2020 has 5 (against 13 in 2019 and 15 in 2021). So June alone
 * is excluded - March was disrupted but did run, and dropping it would hide
 * papers that exist.
 *
 * November 2026 is also excluded because, as of the latest catalogue
 * verification, that future sitting has neither papers nor mark schemes yet.
 * Keyed `${series}${year}` so each unavailable sitting is one entry.
 */
export const unavailableSittings: ReadonlySet<string> = new Set([
  's2020', // Cancelled worldwide.
  'w2026', // This future series has not been sat or published yet.
]);

/** Syllabus-specific sittings absent from the configured paper mirror. */
const unavailableSeriesByCode: Readonly<Record<string, ReadonlySet<string>>> = {
  '0654': new Set(['m2017', 's2017', 'w2017', 'm2018', 'm2019', 'm2020']),
};

/** Individual exceptions left after applying the series and variant rules. */
const unavailablePapers: ReadonlySet<string> = new Set([
  '2281_w23_13',
  '9700_m20_12',
  '9708_s24_12',
]);

export const CATALOGUE_YEARS: number[] = Array.from(
  { length: LATEST_YEAR - EARLIEST_YEAR + 1 },
  (_, i) => LATEST_YEAR - i,
);

/** Distinct subjects in the catalogue, for the subject multiselect. */
export interface CatalogueSubject {
  code: string;
  subject: string;
  qualification: Qualification;
  /** 'Physics (0625)' - the code disambiguates Physics IGCSE from Physics A Level. */
  display: string;
}

export const CATALOGUE_SUBJECTS: CatalogueSubject[] = (() => {
  const seen = new Map<string, CatalogueSubject>();
  for (const p of SOLVABLE_PAPERS) {
    if (seen.has(p.code)) continue;
    seen.set(p.code, {
      code: p.code,
      subject: p.subject,
      qualification: p.qualification,
      display: `${p.subject} (${p.code})`,
    });
  }
  return [...seen.values()].sort(
    (a, b) => a.subject.localeCompare(b.subject) || a.code.localeCompare(b.code),
  );
})();

/**
 * Artwork fallback.
 *
 * codeToIcon/codeToBg are keyed by the 32 subject codes the old mock grid
 * used, which does not include the A Level or O Level syllabuses above. Rather
 * than draw ten new icons, each falls back to its IGCSE counterpart - 9702
 * Physics borrows 0625's atom - and anything unmapped gets the neutral
 * background instead of a broken <img>.
 */
const ART_ALIAS: Record<string, string> = {
  '9700': '0610', '5090': '0610', '0653': '0610',
  '9701': '0620', '5070': '0620', '0654': '0620',
  '9702': '0625', '5054': '0625',
  '9708': '0455', '2281': '0455',
};

export function iconForCode(code: string): string {
  return codeToIcon[code] ?? codeToIcon[ART_ALIAS[code] ?? ''] ?? '';
}

export function backgroundForCode(code: string): string {
  return codeToBg[code] ?? codeToBg[ART_ALIAS[code] ?? ''] ?? codeToBg.default;
}

/** One card in the grid: a single, specific, fetchable paper. */
export interface PaperEntry {
  /** The solver's route parameter and the exam_attempts primary key: '0620_s24_12'. */
  id: string;
  code: string;
  subject: string;
  qualification: Qualification;
  label: string;
  paperNumber: number;
  variant: number;
  series: ExamSeries;
  examYear: number;
  icon: string;
  background: string;
}

/** '0620/s25/12' - the Cambridge shorthand shown in a card's footer. */
export function condensedLabel(entry: PaperEntry): string {
  const yy = String(entry.examYear % 100).padStart(2, '0');
  return `${entry.code}/${entry.series}${yy}/${entry.paperNumber}${entry.variant}`;
}

export interface CatalogueFilter {
  subjectCodes: string[];
  examYears: number[];
  series: ExamSeries[];
  variants: number[];
}

/**
 * Expand the catalogue into individual papers under a filter.
 *
 * An EMPTY array in any field means "no constraint", matching the convention
 * StatsFilter already uses - not "match nothing", which would make the grid
 * blank until every filter was touched.
 */
export function buildPaperEntries(filter: CatalogueFilter): PaperEntry[] {
  const { subjectCodes, examYears, series, variants } = filter;
  const years = examYears.length ? examYears : CATALOGUE_YEARS;
  const entries: PaperEntry[] = [];

  for (const paper of SOLVABLE_PAPERS) {
    if (subjectCodes.length && !subjectCodes.includes(paper.code)) continue;

    for (const year of years) {
      if (!CATALOGUE_YEARS.includes(year)) continue;
      const yy = String(year % 100).padStart(2, '0');

      for (const s of paper.series) {
        if (series.length && !series.includes(s)) continue;
        // A cancelled sitting has no papers to offer. Filtered here rather
        // than removed from CATALOGUE_YEARS because 2020 itself is a real
        // year - November 2020 was sat as normal.
        if (unavailableSittings.has(`${s}${year}`)) continue;
        if (unavailableSeriesByCode[paper.code]?.has(`${s}${year}`)) continue;

        for (const variant of paper.variantsBySeries[s] ?? []) {
          if (variants.length && !variants.includes(variant)) continue;

          const id = `${paper.code}_${s}${yy}_${paper.paperNumber}${variant}`;
          if (unavailablePapers.has(id)) continue;

          entries.push({
            id,
            code: paper.code,
            subject: paper.subject,
            qualification: paper.qualification,
            label: paper.label,
            paperNumber: paper.paperNumber,
            variant,
            series: s,
            examYear: year,
            icon: iconForCode(paper.code),
            background: backgroundForCode(paper.code),
          });
        }
      }
    }
  }

  // Newest first, then subject, then paper - so the default view opens on the
  // newest supported year.
  entries.sort(
    (a, b) =>
      b.examYear - a.examYear ||
      a.subject.localeCompare(b.subject) ||
      a.code.localeCompare(b.code) ||
      a.paperNumber - b.paperNumber ||
      a.series.localeCompare(b.series) ||
      a.variant - b.variant,
  );

  return entries;
}
