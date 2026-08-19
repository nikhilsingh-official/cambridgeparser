// ==========================================================================
//
// Shared plumbing for the read layer. Before this directory existed the app
// performed ZERO reads - every view in schema.sql was unconsumed.
//
// Two rules hold for everything in queries/:
//
//   1. Every query takes an explicit `userId` and filters on it. RLS is
//      deliberately deferred until production (FUTURE_WORK.md §3.2), which
//      means Postgres will happily return every user's rows to anyone who
//      asks. Until RLS lands, the user predicate here is the ONLY thing
//      scoping the data, so it is never optional and never inferred.
//
//   2. Errors are unwrapped in one place. PostgrestError is not an Error, so
//      `throw error` produces an object with no stack; unwrap() converts it
//      into something a catch block can actually report.
// ==========================================================================

import type { PostgrestError } from '@supabase/supabase-js';
import { AttemptStatus, type ExamSeries } from '@/lib/types/enums';
import type { IsoDate, SubjectCode } from '@/lib/types/database';

/** the shape every `.select()` resolves to, regardless of table. */
export interface PostgrestResult<T> {
  data: T[] | null;
  error: PostgrestError | null;
}

/**
 * unwrap a PostgREST response into rows, or throw a real Error.
 *
 * `context` names the view so a failure says which query broke - without it
 * every stats failure reports the same unhelpful "relation does not exist".
 */
export async function unwrap<T>(
  context: string,
  promise: PromiseLike<PostgrestResult<T>>,
): Promise<T[]> {
  const { data, error } = await promise;
  if (error) {
    console.error(`[queries/${context}]`, error);
    // message/details/hint are the three fields worth surfacing; `hint` in
    // particular is where Postgres suggests the fix for a missing column.
    throw new Error(
      `${context} failed: ${error.message}` +
        (error.hint ? ` (hint: ${error.hint})` : ''),
    );
  }
  return data ?? [];
}

/**
 * The filter bar on the stats page. Every field is optional; an empty filter
 * means "everything for this user".
 *
 * arrays rather than single values because the page's three multiselects
 * are multi-choice. An empty array means "no constraint", NOT "match nothing" -
 * applyAttemptFilter() skips empty arrays rather than emitting `in.()`, which
 * PostgREST rejects as a syntax error.
 */
export interface StatsFilter {
  subjectCodes?: SubjectCode[];
  examYears?: number[];
  series?: ExamSeries[];
  variants?: number[];
  /** Inclusive lower bound on local_date. */
  from?: IsoDate;
  /** Inclusive upper bound on local_date. */
  to?: IsoDate;
}

/**
 * the minimal surface of a PostgREST query builder that applyAttemptFilter
 * needs. Typed structurally rather than importing PostgrestFilterBuilder,
 * whose generic parameters change between supabase-js minor versions and would
 * otherwise pin this file to one of them.
 *
 * NOT written as `Filterable<Self>` with `T extends Filterable<T>`: that is the
 * natural formulation, but constraining a builder against itself made the
 * compiler expand PostgrestFilterBuilder's generics recursively and fail with
 * TS2589 "type instantiation is excessively deep". The chain is closed over
 * this interface instead, and applyAttemptFilter re-asserts the caller's own
 * type on the way out - which is what keeps `.order()` and `.limit()` usable on
 * the result.
 */
export interface Filterable {
  eq(column: string, value: unknown): Filterable;
  in(column: string, values: readonly unknown[]): Filterable;
  gte(column: string, value: unknown): Filterable;
  lte(column: string, value: unknown): Filterable;
}

/**
 * Apply the standard stats filter to any query over a relation that exposes
 * `user_id`, `subject_code`, `exam_year`, `series`, `variant` and `local_date`.
 *
 * `userId` is a separate required argument rather than part of StatsFilter
 * so it cannot be forgotten - see rule 1 at the top of this file.
 */
export function applyAttemptFilter<T>(
  query: T,
  userId: string,
  filter: StatsFilter = {},
): T {
  // the two casts are the price of not depending on PostgREST's generic
  // signature. They are confined to this function; every caller stays fully
  // typed because T is returned unchanged.
  let q = (query as Filterable).eq('user_id', userId);

  if (filter.subjectCodes?.length) q = q.in('subject_code', filter.subjectCodes);
  if (filter.examYears?.length)    q = q.in('exam_year', filter.examYears);
  if (filter.series?.length)       q = q.in('series', filter.series);
  if (filter.variants?.length)     q = q.in('variant', filter.variants);
  if (filter.from)                 q = q.gte('local_date', filter.from);
  if (filter.to)                   q = q.lte('local_date', filter.to);

  return q as unknown as T;
}

/**
 * re-exported so query modules get the status value without each importing
 * from two places. Most stats exclude in-progress and abandoned attempts: a
 * half-finished paper has a real duration but a meaningless score.
 */
export const COMPLETED = AttemptStatus.Completed;
