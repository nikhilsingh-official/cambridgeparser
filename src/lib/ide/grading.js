// Submits a student answer to the grading AI. The browser never holds the
// provider key: it invokes the authenticated Supabase grade Edge Function.
// The wasm parse result travels with the request so the endpoint needs no Rust
// binary and can persist the model-computed score through its trusted RPC.
//
// the client now comes from the app's single auth store rather than the
// IDE's own `services/supabase` - one app, one Supabase client, one session.

import { supabase } from '@/stores/useAuth'

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
  const requestBody = {
    record_id: record.id,
    source,
    answer_kind: answerKind,
    // advisory and not a secret - it only decides which of the student's
    // own calendar days the endpoint files the submission on.
    client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    parse: {
      ok: parse.ok,
      ast_version: parse.ast_version,
      statements: parse.statements || [],
      diagnostics: parse.diagnostics || [],
    },
  }
  let data
  try {
    const response = await supabase.functions.invoke('grade', {
      body: requestBody,
    })
    data = response.data
    if (response.error) {
      // FunctionsHttpError keeps the real Response in context. Read the
      // grading-result body so quota/config errors render like successful calls.
      const errorResponse = response.error.context
      if (errorResponse instanceof Response) {
        data = await errorResponse.json().catch(() => null)
        if (errorResponse.status === 429 && data?.schema_version === 'grading-result/v1') {
          const retryAfter = Number(errorResponse.headers.get('Retry-After'))
          const wait = Number.isFinite(retryAfter) && retryAfter > 0
            ? ` Try again in ${Math.ceil(retryAfter / 60)} minute(s).`
            : ''
          data.error = `${data.error || 'AI grading limit reached.'}${wait}`
          return data
        }
      }
      if (!data) throw response.error
    }
  } catch (error) {
    throw new Error(`Could not reach the grading service: ${error.message || error}`)
  }
  // A grading-result/v1 with ok:false is a *handled* grading failure (e.g. no
  // API key) that the UI should display, not throw. Only throw when the
  // response is not a grading result at all.
  if (data.schema_version !== 'grading-result/v1') {
    throw new Error(data?.error || 'Grading failed')
  }
  return data
}
