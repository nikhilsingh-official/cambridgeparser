// Submits a student answer to the grading AI. The browser never holds the
// OpenRouter key: it POSTs to /api/grade, which is the Python pipeline in dev
// (vite plugin) and a Firebase Cloud Function in production. The wasm parse
// result travels with the request so the endpoint needs no Rust binary.

import { auth } from './firebase'

const GRADE_URL = '/api/grade'

/**
 * @param {object} record  the pseudocode-question-record/v1 for the question
 * @param {string} source  the student's pseudocode
 * @param {object} parse   the wasm compiler result ({ ok, statements, diagnostics, ast_version })
 * @returns {Promise<object>} a grading-result/v1 payload
 */
export async function gradeSubmission(record, source, parse, answerKind = 'pseudocode') {
  const user = auth.currentUser
  if (!user) throw new Error('Sign in is required to use AI grading.')
  const token = await user.getIdToken()
  let response
  try {
    response = await fetch(GRADE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        record_id: record.id,
        source,
        answer_kind: answerKind,
        parse: {
          ok: parse.ok,
          ast_version: parse.ast_version,
          statements: parse.statements || [],
          diagnostics: parse.diagnostics || [],
        },
      }),
    })
  } catch (error) {
    throw new Error(`Could not reach the grading service: ${error.message || error}`)
  }

  const text = await response.text()
  let data
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error(
      `Grading service returned a non-JSON response (${response.status}). `
      + 'Is the grading endpoint running?',
    )
  }
  if (response.status === 429) {
    const retryAfter = Number(response.headers.get('Retry-After'))
    const wait = Number.isFinite(retryAfter) && retryAfter > 0
      ? ` Try again in ${Math.ceil(retryAfter / 60)} minute(s).`
      : ''
    throw new Error(`${data.error || 'AI grading limit reached.'}${wait}`)
  }
  // A grading-result/v1 with ok:false is a *handled* grading failure (e.g. no
  // API key) that the UI should display, not throw. Only throw when the
  // response is not a grading result at all.
  if (data.schema_version !== 'grading-result/v1') {
    throw new Error(data.error || `Grading failed (${response.status})`)
  }
  return data
}
