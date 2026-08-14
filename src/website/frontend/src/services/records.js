// `import.meta.env` is supplied by Vite in the browser. The fallback keeps the
// pure record helpers importable from Node's built-in test runner too.
const BASE_URL = import.meta.env?.BASE_URL || '/'
const RECORDS_URL = `${BASE_URL}resources/pseudocode_question_records.json`
const LAYOUTS_URL = `${BASE_URL}resources/question_layouts.json`

export async function loadQuestionRecords() {
  const response = await fetch(RECORDS_URL)
  if (!response.ok) {
    throw new Error(`Cannot load ${RECORDS_URL}: ${response.status}`)
  }
  return response.json()
}

export async function loadQuestionLayouts() {
  const response = await fetch(LAYOUTS_URL)
  if (!response.ok) {
    throw new Error(`Cannot load ${LAYOUTS_URL}: ${response.status}`)
  }
  return response.json()
}

export function markerLabel(record) {
  const key = record?.segment_key || {}
  let label = `Q${key.question_marker ?? '?'}`
  if (key.primary_marker) label += key.primary_marker
  if (key.secondary_marker) label += key.secondary_marker
  return label
}

export function marksFor(record) {
  const markScheme = record?.mark_scheme || {}
  return markScheme.max_marks ?? markScheme.marks_value ?? record?.qp_marks_value ?? '?'
}

export function recordSummary(record) {
  return {
    id: record.id,
    paperCode: record.paper_code || '',
    label: markerLabel(record),
    marks: marksFor(record),
    pointCount: record.marking_point_count ?? (record.mark_scheme?.marking_points || []).length,
    questionText: record.question_text || '',
  }
}

// The measured "total question context" (part (a) tables, intros, prior
// subparts) carries the answer-line dot/underscore runs from the scan. Strip
// those and tidy whitespace so the context reads cleanly above the question.
export function cleanContextText(record) {
  const raw = record?.question_context_text || ''
  return raw
    .replace(/[.·•…_]{4,}/g, ' ') // repeated dot/underscore answer blanks
    .replace(/-{4,}/g, ' ') // long dash runs (single hyphens in words survive)
    .replace(/[ \t]{2,}/g, ' ') // collapse runs of spaces/tabs
    .replace(/[ \t]+\n/g, '\n') // trailing spaces before newlines
    .replace(/\n{3,}/g, '\n\n') // collapse 3+ blank lines to one
    .trim()
}

function isInlineBlank(token, page) {
  // Full-width dotted answer lines are writing space, not individual gaps.
  // True gap-fill blanks occupy only part of their question page.
  const pageWidth = page.width ?? page.pageWidth
  return token.kind === 'blank' && Number.isFinite(pageWidth) && token.w < pageWidth * 0.8
}

function hasInlineBlankTokens(layout) {
  return Boolean(layout?.pages?.some((page) => (
    page.tokens?.some((token) => isInlineBlank(token, page))
  )))
}

export function isFillBlankQuestion(record, layout) {
  // Context can contain instructions from an earlier sub-question. Only the
  // selected question expresses how this answer should be entered.
  const text = String(record?.question_text || '').toLowerCase()
  const explicitFillPrompt = [
    /\bfill in (?:the )?(?:gaps?|blanks?)\b/,
    /\bcomplete\b.{0,100}\b(?:pseudocode|algorithm|trace table|statements?|expressions?)\b/s,
    /\b(?:pseudocode|algorithm|trace table|statements?|expressions?)\b.{0,100}\bcomplete\b/s,
    /\b(?:missing|numbered)\s+(?:lines?|statements?|parts?|gaps?|blanks?)\b/,
  ].some((pattern) => pattern.test(text))

  if (!explicitFillPrompt) return false
  // These require a prose/number response alongside code, so a code editor is
  // more faithful than turning only one of their answer lines into a field.
  if (/\b(?:line number|number of each error|correct(?:ed)? pseudocode)\b/.test(text)) {
    return false
  }
  // When a layout is supplied, never replace the editor with an empty fields
  // panel. Callers without a layout can still use this helper for text-only UI.
  return layout === undefined || hasInlineBlankTokens(layout)
}

export function layoutLines(layout) {
  const lines = []
  for (const page of layout?.pages || []) {
    const pageLines = []
    const tokens = (page.tokens || [])
      .map((token, index) => ({ ...token, index, key: `${page.page_index}:${index}` }))
      .sort((a, b) => a.y - b.y || a.x - b.x)
    for (const token of tokens) {
      const line = pageLines.find((candidate) => Math.abs(candidate.y - token.y) <= 2)
      if (line) {
        line.tokens.push(token)
      } else {
        pageLines.push({ pageIndex: page.page_index, pageWidth: page.width, y: token.y, tokens: [token] })
      }
    }
    for (const line of pageLines) {
      line.tokens.sort((a, b) => a.x - b.x)
      lines.push(line)
    }
  }
  return lines
}

export function fillBlankFields(layout) {
  const fields = []
  for (const line of layoutLines(layout)) {
    const context = line.tokens
      .map((token) => token.kind === 'blank' ? '[blank]' : (token.text || ''))
      .join(' ')
      .replace(/\s+/g, ' ')
      .replace(/\s+([,):])/g, '$1')
      .trim()
    for (const token of line.tokens) {
      if (token.kind === 'blank') fields.push({ key: token.key, context })
    }
  }
  return fields
}

export function assembleFillSource(layout, fillValues = {}) {
  // PDF extraction can omit fixed operators and corrupt footer text, so do not
  // pretend its geometry is compilable source. Submit a lossless answer sheet;
  // the grading service combines it with the trusted full question and rubric.
  const fields = fillBlankFields(layout)
  if (!fields.some((field) => String(fillValues[field.key] || '').trim())) return ''
  return fields.map((field, index) => (
      `Blank ${index + 1} (${field.context || 'no surrounding text'}): `
      + String(fillValues[field.key] || '').trim()
    ))
    .join('\n')
    .trim()
}
