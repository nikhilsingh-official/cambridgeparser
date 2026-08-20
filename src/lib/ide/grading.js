// Submits a student answer to the grading AI. The browser never holds the
// provider key: it POSTs to /api/grade, a Vercel Python Function that reads it
// from the server-side environment. The wasm parse result travels with the
// request so the endpoint needs no Rust binary.
//
// the client now comes from the app's single auth store rather than the
// IDE's own `services/supabase` - one app, one Supabase client, one session.

import { supabase } from '@/stores/useAuth'

const GRADE_URL = '/api/grade'

/**
 * @param {object} record  the pseudocode-question-record/v1 for the question
 * @param {string} source  the student's pseudocode
 * @param {object} parse   the wasm compiler result ({ ok, statements, diagnostics, ast_version })
 * @returns {Promise<object>} a grading-result/v1 payload
 */
export async function gradeSubmission(record, source, parse, answerKind = 'pseudocode') {
  // The Supabase access token is a JWT the endpoint verifies against the
  // project; getSession() refreshes it first if it is close to expiry, so a
  // long editing session cannot submit with a stale token.
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession()
  if (sessionError || !sessionData.session) {
    throw new Error('Sign in is required to use AI grading.')
  }
  const token = sessionData.session.access_token
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
    if (data.schema_version === 'grading-result/v1') {
      data.error = `${data.error || 'AI grading limit reached.'}${wait}`
      return data
    }
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
