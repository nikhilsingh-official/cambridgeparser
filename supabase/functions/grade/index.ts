// ==========================================================================
//
// Authenticated Supabase Edge endpoint for grading one trusted corpus record.
// The user-scoped client spends quota; the server-scoped credential is used
// only for the service-only history RPC after a successful model decision.
// ==========================================================================

import 'jsr:@supabase/functions-js/edge-runtime.d.ts';
import { createClient } from 'npm:@supabase/supabase-js@2.84.0';
import { gradeTrustedRecord, RESULT_SCHEMA_VERSION } from './grading.ts';
// import the application's committed corpus into the Edge bundle. This is
// the browser corpus intentionally omits answers so opening DevTools cannot
// reveal a mark scheme before submission. The Edge Function ships its own
// trusted copy containing the official answer and extracted marking points.
import gradingCorpus from './pseudocode_question_records.json' with { type: 'json' };

const MAX_REQUEST_BYTES = 256_000;
const MAX_SOURCE_CHARS = 20_000;
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

type JsonObject = Record<string, any>;
let recordsById: Map<string, JsonObject> | null = null;

function jsonResponse(status: number, payload: JsonObject, extra: Record<string, string> = {}): Response {
  return Response.json(payload, {
    status,
    headers: { ...CORS_HEADERS, 'Cache-Control': 'no-store', ...extra },
  });
}

function errorPayload(message: string, markScheme?: JsonObject): JsonObject {
  return {
    schema_version: RESULT_SCHEMA_VERSION,
    ok: false,
    result: null,
    error: message,
    ...(markScheme ? { mark_scheme: markScheme } : {}),
  };
}

function parseNamedSecret(name: 'SUPABASE_PUBLISHABLE_KEYS' | 'SUPABASE_SECRET_KEYS'): string | null {
  const raw = Deno.env.get(name);
  if (!raw) return null;
  try {
    return (JSON.parse(raw) as Record<string, string>).default ?? null;
  } catch {
    return null;
  }
}

function publishableKey(): string | null {
  return parseNamedSecret('SUPABASE_PUBLISHABLE_KEYS') ?? Deno.env.get('SUPABASE_ANON_KEY') ?? null;
}

function secretKey(): string | null {
  return parseNamedSecret('SUPABASE_SECRET_KEYS') ?? Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? null;
}

async function loadRecords(): Promise<Map<string, JsonObject>> {
  if (recordsById) return recordsById;
  recordsById = new Map(
    ((gradingCorpus as { records?: JsonObject[] }).records ?? [])
      .filter(record => record?.id != null)
      .map(record => [String(record.id), record]),
  );
  return recordsById;
}

async function recordTrustedAttempt(
  userId: string,
  request: JsonObject,
  result: JsonObject,
): Promise<void> {
  if (!result.ok || !result.result) return;
  const url = Deno.env.get('SUPABASE_URL');
  const key = secretKey();
  if (!url || !key) throw new Error('trusted database credentials unavailable');
  const headers: Record<string, string> = { apikey: key, 'Content-Type': 'application/json' };
  // legacy service_role keys are JWTs and need both headers. New sb_secret
  // keys must only be sent as apikey; the gateway mints the elevated role.
  if (!key.startsWith('sb_secret_')) headers.Authorization = `Bearer ${key}`;
  const response = await fetch(`${url}/rest/v1/rpc/record_ide_attempt_trusted`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      p_user_id: userId,
      p_record_id: String(request.record_id),
      p_score: result.result.total_awarded,
      p_max_marks: result.result.max_marks,
      p_source: typeof request.source === 'string' ? request.source.slice(0, MAX_SOURCE_CHARS) : null,
      p_answer_kind: typeof request.answer_kind === 'string' ? request.answer_kind : null,
      p_points: Array.isArray(result.result.points) ? result.result.points : null,
      p_client_timezone: typeof request.client_timezone === 'string' ? request.client_timezone : null,
    }),
  });
  if (!response.ok) throw new Error(`trusted history RPC returned ${response.status}`);
}

Deno.serve(async request => {
  if (request.method === 'OPTIONS') return new Response('ok', { headers: CORS_HEADERS });
  if (request.method !== 'POST') return jsonResponse(405, errorPayload('POST required (this endpoint grades one submission)'));

  const declaredLength = Number(request.headers.get('content-length') ?? 0);
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    return jsonResponse(413, errorPayload('request is too large'));
  }

  const token = request.headers.get('authorization')?.replace(/^Bearer\s+/i, '');
  const url = Deno.env.get('SUPABASE_URL');
  const publicKey = publishableKey();
  if (!token || !url || !publicKey) {
    return jsonResponse(401, errorPayload('Sign in is required to use AI grading.'));
  }

  const userClient = createClient(url, publicKey, {
    global: { headers: { Authorization: `Bearer ${token}` } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: userData, error: userError } = await userClient.auth.getUser(token);
  if (userError || !userData.user) {
    return jsonResponse(401, errorPayload('Sign in is required to use AI grading.'));
  }

  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > MAX_REQUEST_BYTES) {
    return jsonResponse(413, errorPayload('request is too large'));
  }
  let payload: JsonObject;
  try {
    payload = JSON.parse(text);
  } catch (error) {
    return jsonResponse(400, errorPayload(`invalid request JSON: ${error instanceof Error ? error.message : error}`));
  }
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return jsonResponse(400, errorPayload('request JSON must be an object'));
  }

  const records = await loadRecords();
  const record = records.get(String(payload.record_id));
  if (!record) return jsonResponse(400, errorPayload('request.record_id is not a trusted question record'));
  const markScheme = record.mark_scheme ?? {};
  if (typeof payload.source !== 'string') return jsonResponse(400, errorPayload('request.source must be a string', markScheme));
  if (payload.source.length > MAX_SOURCE_CHARS) return jsonResponse(400, errorPayload(`request.source exceeds ${MAX_SOURCE_CHARS} characters`, markScheme));
  if (!payload.parse || typeof payload.parse !== 'object' || Array.isArray(payload.parse)) {
    return jsonResponse(400, errorPayload('request.parse must be an object', markScheme));
  }
  const answerKind = payload.answer_kind ?? 'pseudocode';
  if (!['pseudocode', 'fill_blank_sheet'].includes(answerKind)) {
    return jsonResponse(400, errorPayload('request.answer_kind is not supported', markScheme));
  }

  const googleKey = Deno.env.get('GOOGLE_AI_STUDIO_API_KEY') ?? undefined;
  const openRouterKey = Deno.env.get('OPENROUTER_API_KEY') ?? undefined;
  if (!googleKey && !openRouterKey) {
    return jsonResponse(503, errorPayload(
      'AI grading is not configured: set GOOGLE_AI_STUDIO_API_KEY (or OPENROUTER_API_KEY).',
      markScheme,
    ));
  }

  const { data: quota, error: quotaError } = await userClient.rpc('consume_grading_quota');
  if (quotaError || !quota || typeof quota !== 'object') {
    return jsonResponse(503, errorPayload('AI grading is temporarily unavailable. Please try again.', markScheme));
  }
  if (quota.allowed !== true) {
    const retry = Number.isInteger(quota.retry_after_seconds) ? quota.retry_after_seconds : 60;
    return jsonResponse(429, {
      ...errorPayload('AI grading limit reached. Try again later.', markScheme),
      retry_after_seconds: retry,
    }, { 'Retry-After': String(retry) });
  }

  const parsedAnswer = {
    schema_version: 'parsed-answer/v1',
    source_text: payload.source,
    answer_kind: answerKind,
    parse: {
      ok: Boolean(payload.parse.ok),
      ast_version: payload.parse.ast_version ?? 'cambridge-pseudocode-ast/v1',
      ast: { statements: payload.parse.statements ?? [] },
      diagnostics: payload.parse.diagnostics ?? [],
    },
  };
  const result = await gradeTrustedRecord(record, parsedAnswer, {
    googleKey,
    googleModels: Deno.env.get('GOOGLE_AI_MODEL')
      ? [Deno.env.get('GOOGLE_AI_MODEL')!]
      : Deno.env.get('GOOGLE_AI_MODELS')?.split(',').map(value => value.trim()).filter(Boolean),
    googleBaseUrl: Deno.env.get('GOOGLE_AI_BASE_URL') ?? undefined,
    googleThinkingBudget: Number.isFinite(Number(Deno.env.get('GOOGLE_AI_THINKING_BUDGET')))
      ? Number(Deno.env.get('GOOGLE_AI_THINKING_BUDGET'))
      : undefined,
    openRouterKey,
    openRouterModel: Deno.env.get('OPENROUTER_MODEL') ?? undefined,
    openRouterBaseUrl: Deno.env.get('OPENROUTER_BASE_URL') ?? undefined,
    openRouterProviderOnly: Deno.env.get('OPENROUTER_PROVIDER_ONLY')
      ?.split(',').map(value => value.trim()).filter(Boolean),
    openRouterProviderSort: Deno.env.get('OPENROUTER_PROVIDER_SORT') ?? undefined,
  });
  result.mark_scheme = markScheme;
  result.rate_limit_remaining = quota.remaining;

  try {
    await recordTrustedAttempt(userData.user.id, payload, result);
    result.history_saved = result.ok ? true : null;
  } catch (error) {
    // grading succeeded; history is best-effort and failure is visible in
    // server logs without throwing away a result the student waited for.
    console.error('record_ide_attempt_trusted failed:', error);
    result.history_saved = false;
    result.history_error = 'The grade was returned but could not be added to progress history.';
  }

  return jsonResponse(result.ok || ['google-ai-studio', 'openrouter'].includes(result.provider) ? 200 : 400, result);
});
