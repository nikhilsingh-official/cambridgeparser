// ==========================================================================
//
// The Paper Browser's filter, shared between the header (which edits it) and
// the page (which applies it). Its own module so the two components do not
// have to import each other.
// ==========================================================================

import type { ExamSeries } from '@/lib/types/enums';
import { LATEST_YEAR } from '@/constants/paperCatalogue';

/**
 * Attempt state, as the browser cares about it. Deliberately NOT the SQL
 * attempt_status enum: 'unattempted' is the absence of a row, which that enum
 * cannot express, and it is the single most useful thing to filter on.
 */
export const PaperProgress = {
  Unattempted: 'unattempted',
  InProgress: 'in_progress',
  Completed: 'completed',
} as const;
export type PaperProgress = typeof PaperProgress[keyof typeof PaperProgress];

export const PAPER_PROGRESS_LABEL: Record<PaperProgress, string> = {
  unattempted: 'Not attempted',
  in_progress: 'In progress',
  completed: 'Completed',
};

export interface BrowserFilter {
  subjectCodes: string[];
  examYears: number[];
  series: ExamSeries[];
  variants: number[];
  progress: PaperProgress[];
}

/**
 * The view the browser opens on.
 *
 * Not "everything": the catalogue expands to roughly four thousand papers, and
 * a grid of four thousand cards is not a browser, it is a denial of service on
 * the person using it. One year and one series is ~45 cards - enough to fill
 * the grid, few enough to scan - and every other combination is one click away.
 */
export function defaultFilter(): BrowserFilter {
  return {
    subjectCodes: [],
    examYears: [LATEST_YEAR],
    series: ['s'],
    variants: [],
    progress: [],
  };
}
