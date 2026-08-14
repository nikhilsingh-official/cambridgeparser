// Syllabus-tag helpers shared by the problems table and the IDE explorer.
//
// Tags arrive on each record already expanded by `build_final_records`
// ({slug, label, syllabus_ref, section, section_label, description}), so
// everything here is derived from the records themselves — there is no separate
// vocabulary fetch, and a tag that no question carries never appears as a facet
// the user can click into an empty result.

export const MATCH_ANY = 'any'
export const MATCH_ALL = 'all'

export function recordTags(record) {
  return record?.syllabus_tags || []
}

export function recordTagSlugs(record) {
  return recordTags(record).map((tag) => tag.slug)
}

/**
 * Every tag present in `records`, with the number of records carrying it.
 * Ordered by count descending, then label, so the busiest facets lead.
 */
export function buildTagIndex(records) {
  const index = new Map()
  for (const record of records || []) {
    for (const tag of recordTags(record)) {
      const existing = index.get(tag.slug)
      if (existing) {
        existing.count += 1
      } else {
        index.set(tag.slug, { ...tag, count: 1 })
      }
    }
  }
  return [...index.values()].sort(
    (a, b) => b.count - a.count || a.label.localeCompare(b.label),
  )
}

/**
 * Group tags under their syllabus section, sections in numeric order and tags
 * alphabetical within a section. This is the shape the facet list renders.
 */
export function groupTagsBySection(tags) {
  const groups = new Map()
  for (const tag of tags) {
    if (!groups.has(tag.section)) {
      groups.set(tag.section, {
        section: tag.section,
        label: tag.section_label,
        tags: [],
      })
    }
    groups.get(tag.section).tags.push(tag)
  }
  const ordered = [...groups.values()].sort(
    (a, b) => Number(a.section) - Number(b.section),
  )
  for (const group of ordered) {
    group.tags.sort((a, b) => a.label.localeCompare(b.label))
  }
  return ordered
}

// Free-text search terms. Splitting on whitespace and requiring *every* term to
// match means "file record" narrows to questions about both, which is what a
// space in a search box is normally taken to mean. A quoted phrase is kept
// whole so an exact string can still be searched.
export function parseQuery(query) {
  const terms = String(query || '')
    .toLowerCase()
    .match(/"[^"]*"|\S+/g)
  if (!terms) return []
  return terms
    .map((term) => term.replace(/^"|"$/g, '').trim())
    .filter(Boolean)
}

function haystack(record) {
  return [
    record.paper_code,
    record.segment_key?.question_marker,
    record.segment_key?.primary_marker,
    record.segment_key?.secondary_marker,
    record.question_text,
    record.mark_scheme?.answer_text,
    ...recordTags(record).flatMap((tag) => [tag.label, tag.slug]),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

export function matchesQuery(record, terms) {
  if (!terms.length) return true
  const text = haystack(record)
  return terms.every((term) => text.includes(term))
}

export function matchesTags(record, slugs, mode) {
  if (!slugs.length) return true
  const present = new Set(recordTagSlugs(record))
  return mode === MATCH_ALL
    ? slugs.every((slug) => present.has(slug))
    : slugs.some((slug) => present.has(slug))
}

/**
 * Apply the search box and the tag facets together. Search and tags always
 * combine with AND (narrowing); `mode` only decides how multiple *tags* combine.
 */
export function filterRecords(records, { query = '', tags = [], mode = MATCH_ANY } = {}) {
  const terms = parseQuery(query)
  const slugs = [...tags]
  if (!terms.length && !slugs.length) return records || []
  return (records || []).filter(
    (record) => matchesQuery(record, terms) && matchesTags(record, slugs, mode),
  )
}

/**
 * How many records each facet would still match if it were the next tag added.
 * Counting against the *query-filtered* set (not the tag-filtered one) keeps a
 * facet's number stable while the user toggles sibling tags in "any" mode,
 * which is what makes the counts readable rather than jumpy.
 */
export function facetCounts(records, query) {
  const terms = parseQuery(query)
  const counts = new Map()
  for (const record of records || []) {
    if (!matchesQuery(record, terms)) continue
    for (const slug of recordTagSlugs(record)) {
      counts.set(slug, (counts.get(slug) || 0) + 1)
    }
  }
  return counts
}

// Filter state <-> URL query, so a filtered view is linkable and the tag chips
// on a question can deep-link into the problems table.
export function tagsFromQueryParam(value) {
  if (!value) return []
  const raw = Array.isArray(value) ? value.join(',') : String(value)
  return raw.split(',').map((slug) => slug.trim()).filter(Boolean)
}

export function tagsToQueryParam(slugs) {
  return slugs.length ? slugs.join(',') : undefined
}
