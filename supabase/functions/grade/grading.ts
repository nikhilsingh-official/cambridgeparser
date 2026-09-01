// ==========================================================================
//
// Provider-independent grading contract plus Google/OpenRouter transports.
// The browser supplies its WASM parse; this module supplies the trusted record,
// strict output schema, provider rotation/fallback, validation and score cap.
// ==========================================================================

export const RESULT_SCHEMA_VERSION = 'grading-result/v1';
export const DEFAULT_GOOGLE_MODELS = [
  'gemini-3.5-flash-lite',
  'gemini-3.6-flash',
  'gemma-4-31b-it',
  'gemini-3.1-flash-lite',
];
export const DEFAULT_OPENROUTER_MODEL = 'google/gemini-2.5-flash';

type JsonObject = Record<string, any>;
type FetchLike = typeof fetch;

const gradingProperties = {
  total_awarded: { type: 'integer', minimum: 0 },
  max_marks: { type: 'integer', minimum: 0 },
  points: {
    type: 'array',
    items: {
      type: 'object',
      additionalProperties: false,
      properties: {
        marking_point_id: { type: 'string', minLength: 1 },
        awarded: { type: 'boolean' },
        marks_awarded: { type: 'integer', minimum: 0 },
        confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        evidence: { type: 'string' },
        concerns: { type: 'array', items: { type: 'string' } },
      },
      required: [
        'marking_point_id', 'awarded', 'marks_awarded',
        'confidence', 'evidence', 'concerns',
      ],
    },
  },
  overall_explanation: { type: 'string' },
};

const requiredGradingFields = [
  'total_awarded', 'max_marks', 'points', 'overall_explanation',
];

const openRouterResponseFormat = {
  type: 'json_schema',
  json_schema: {
    name: 'grading_result',
    strict: true,
    schema: {
      type: 'object',
      additionalProperties: false,
      properties: gradingProperties,
      required: requiredGradingFields,
    },
  },
};

const googleResponseSchema = {
  type: 'object',
  properties: {
    ...gradingProperties,
    points: {
      ...gradingProperties.points,
      items: {
        ...gradingProperties.points.items,
        additionalProperties: undefined,
        propertyOrdering: [
          'marking_point_id', 'awarded', 'marks_awarded',
          'confidence', 'evidence', 'concerns',
        ],
      },
    },
  },
  required: requiredGradingFields,
  propertyOrdering: requiredGradingFields,
};

function markingPointGroups(points: JsonObject[]): JsonObject[][] {
  const groups = new Map<number, JsonObject[]>();
  for (const point of points) {
    const key = Number.isInteger(point.alt_group) ? point.alt_group : 0;
    groups.set(key, [...(groups.get(key) ?? []), point]);
  }
  return [...groups.entries()].sort(([a], [b]) => a - b).map(([, group]) => group);
}

function groupMarks(points: JsonObject[]): number {
  return points.reduce((total, point) => total + (Number.isInteger(point.marks) ? point.marks : 1), 0);
}

export function resolveMaxMarks(record: JsonObject): number | null {
  const scheme = record.mark_scheme ?? {};
  for (const key of ['max_marks', 'marks_value']) {
    if (Number.isInteger(scheme[key])) return scheme[key];
  }
  const groups = markingPointGroups(scheme.marking_points ?? []);
  return groups.length ? Math.max(...groups.map(groupMarks)) : null;
}

export function applyMaxMarksCap(payload: JsonObject, cap: number | null): JsonObject {
  if (!Number.isInteger(cap) || (cap as number) < 0) return payload;
  const reported = Number.isInteger(payload.total_awarded)
    ? payload.total_awarded
    : (payload.points ?? []).reduce(
      (sum: number, point: JsonObject) => sum + (Number.isInteger(point.marks_awarded) ? point.marks_awarded : 0),
      0,
    );
  payload.max_marks = cap;
  payload.total_awarded = Math.min(reported, cap as number);
  if (reported > (cap as number)) {
    payload.cap_applied = { reported_total: reported, max_marks: cap };
    const note = `Total capped at the question maximum of ${cap} (marking points supported ${reported}).`;
    payload.overall_explanation = `${payload.overall_explanation ?? ''} ${note}`.trim();
  }
  return payload;
}

export function extractJsonObject(text: string): JsonObject | null {
  let candidate = text.trim();
  const fence = candidate.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/);
  if (fence) candidate = fence[1]!;
  try {
    const parsed = JSON.parse(candidate);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
  } catch { /* try the outermost object below */ }
  const start = candidate.indexOf('{');
  const end = candidate.lastIndexOf('}');
  if (start < 0 || end <= start) return null;
  try {
    const parsed = JSON.parse(candidate.slice(start, end + 1));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function validateGradingPayload(payload: unknown, trustedRecord?: JsonObject): string | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return 'response is not a JSON object';
  const value = payload as JsonObject;
  if (!Number.isInteger(value.total_awarded)) return 'total_awarded must be an integer';
  if (value.total_awarded < 0) return 'total_awarded must be non-negative';
  if (!Number.isInteger(value.max_marks)) return 'max_marks must be an integer';
  if (value.max_marks < 0) return 'max_marks must be non-negative';
  if (value.total_awarded > value.max_marks) return 'total_awarded cannot exceed max_marks';
  if (!Array.isArray(value.points)) return 'points must be a list';
  const responseIds = new Set<string>();
  for (let index = 0; index < value.points.length; index += 1) {
    const point = value.points[index];
    if (!point || typeof point !== 'object' || Array.isArray(point)) return `points[${index}] is not an object`;
    if (typeof point.marking_point_id !== 'string') return `points[${index}].marking_point_id must be a string`;
    if (!point.marking_point_id.trim()) return `points[${index}].marking_point_id cannot be empty`;
    if (responseIds.has(point.marking_point_id)) return `points[${index}].marking_point_id is duplicated`;
    responseIds.add(point.marking_point_id);
    if (typeof point.awarded !== 'boolean') return `points[${index}].awarded must be a boolean`;
    if (!Number.isInteger(point.marks_awarded)) return `points[${index}].marks_awarded must be an integer`;
    if (point.marks_awarded < 0) return `points[${index}].marks_awarded must be non-negative`;
    if (!point.awarded && point.marks_awarded !== 0) return `points[${index}] is unawarded but has marks`;
    if (point.awarded && point.marks_awarded === 0) return `points[${index}] is awarded but has no marks`;
    if (!['high', 'medium', 'low'].includes(point.confidence)) return `points[${index}].confidence is invalid`;
    if (typeof point.evidence !== 'string') return `points[${index}].evidence must be a string`;
    if (!Array.isArray(point.concerns)) return `points[${index}].concerns must be a list`;
    if (!point.concerns.every((concern: unknown) => typeof concern === 'string')) {
      return `points[${index}].concerns must contain only strings`;
    }
  }
  if (typeof value.overall_explanation !== 'string') return 'overall_explanation must be a string';

  if (!trustedRecord) return null;
  const cap = resolveMaxMarks(trustedRecord);
  if (cap !== null && value.max_marks !== cap) return `max_marks must match the trusted maximum of ${cap}`;
  if (cap !== null && value.total_awarded > cap) return `total_awarded cannot exceed the trusted maximum of ${cap}`;

  const trustedPoints: JsonObject[] = trustedRecord.mark_scheme?.marking_points ?? [];
  if (trustedPoints.length) {
    const byId = new Map(trustedPoints.map(point => [String(point.id ?? ''), point]));
    for (let index = 0; index < value.points.length; index += 1) {
      const responsePoint = value.points[index];
      const trustedPoint = byId.get(responsePoint.marking_point_id);
      if (!trustedPoint) return `points[${index}] references an unknown marking point`;
      const available = Number.isInteger(trustedPoint.marks) ? trustedPoint.marks : 1;
      if (responsePoint.marks_awarded > available) {
        return `points[${index}].marks_awarded exceeds the trusted marking point maximum`;
      }
    }
    const missing = [...byId.keys()].find(id => !responseIds.has(id));
    if (missing) return `response is missing trusted marking point ${missing}`;
  }

  const pointTotal = value.points.reduce(
    (sum: number, point: JsonObject) => sum + point.marks_awarded,
    0,
  );
  return pointTotal === value.total_awarded
    ? null
    : `total_awarded must equal the marking-point sum of ${pointTotal}`;
}

export function classifyGoogleFailure(code: number, detail: string): string | null {
  const normalizedDetail = detail.toUpperCase();
  if (code === 429 || normalizedDetail.includes('RESOURCE_EXHAUSTED')) return 'rate_limit';
  if (code === 404 || normalizedDetail.includes('NOT_FOUND')) return 'model_unavailable';
  if ([408, 500, 502, 503, 504].includes(code)) return 'provider_unavailable';
  return null;
}

function compactExamText(text: string): string {
  return text.split('\n').map(line => line
    .replace(/\.{10,}/g, '[answer space]')
    .replace(/\s+/g, ' ')
    .trim())
    .filter(Boolean)
    .filter((line, index, lines) => line !== '[answer space]' || lines[index - 1] !== line)
    .join('\n');
}

function buildMessages(record: JsonObject, parsedAnswer: JsonObject): JsonObject[] {
  const scheme = record.mark_scheme ?? {};
  const points: JsonObject[] = scheme.marking_points ?? [];
  const groups = markingPointGroups(points);
  const maxMarks = resolveMaxMarks(record);
  let pointLines = '';
  let instruction = '';
  if (groups.length > 1) {
    pointLines = groups.map((group, index) =>
      `ALTERNATIVE SOLUTION ${index + 1} (${groupMarks(group)} mark(s) available):\n`
      + group.map(point => `- ${point.id}: ${point.text} (${point.marks ?? 1} mark)`).join('\n')
    ).join('\n\n');
    instruction = `The mark scheme lists ${groups.length} mutually exclusive alternatives. Choose one, award nothing from the others, and never exceed ${maxMarks}.`;
  } else if (points.length) {
    pointLines = points.map(point => `- ${point.id}: ${point.text} (${point.marks ?? 1} mark)`).join('\n');
    instruction = `Judge every marking point independently and never exceed ${maxMarks}.`;
  } else {
    pointLines = `(derive up to ${maxMarks ?? 6} points from the mark-scheme answer using ids auto1, auto2, ...)`;
    instruction = 'Derive marking points from the mark-scheme answer, then judge each independently.';
  }
  const parse = parsedAnswer.parse ?? {};
  const packet: JsonObject = {
    answer_kind: parsedAnswer.answer_kind ?? 'pseudocode',
    question_text: compactExamText(record.question_text ?? ''),
    question_context_text: compactExamText(record.question_context_text ?? ''),
    mark_scheme_answer_text: compactExamText(scheme.answer_text ?? ''),
    max_marks: maxMarks,
    student_source_text: parsedAnswer.source_text ?? '',
    student_ast: parse.ast ?? {},
    parser_ok: parse.ok,
    marking_point_ids: points.map(point => ({
      id: String(point.id ?? ''), text: String(point.text ?? ''),
      marks: Number.isInteger(point.marks) ? point.marks : 1,
      ...(Number.isInteger(point.alt_group) ? { alt_group: point.alt_group } : {}),
    })),
  };
  if (parse.diagnostics?.length) packet.parser_diagnostics = parse.diagnostics;
  let system = 'You are an experienced Cambridge International Computer Science examiner grading pseudocode. '
    + instruction
    + ' Respond with STRICT JSON only matching the supplied response schema. If parser diagnostics exist, grade the source text and mention them in concerns.';
  if (packet.answer_kind === 'fill_blank_sheet') {
    system += ' The answer is an ordered fill-in-the-blank sheet; do not penalize it for lacking a complete AST.';
  }
  return [
    { role: 'system', content: system },
    { role: 'user', content: `GRADING PACKET (JSON):\n${JSON.stringify(packet)}\n\nMARKING POINTS:\n${pointLines}\n\nReturn strict JSON now.` },
  ];
}

function resultFailure(provider: string, model: string, error: string, raw: string | null, fallbackReason?: string): JsonObject {
  return {
    schema_version: RESULT_SCHEMA_VERSION, ok: false, dry_run: false,
    model, provider, result: null, error, raw_response: raw,
    ...(fallbackReason ? { fallback_reason: fallbackReason } : {}),
  };
}

async function fetchWithTimeout(fetcher: FetchLike, url: string, init: RequestInit): Promise<Response> {
  return fetcher(url, { ...init, signal: AbortSignal.timeout(120_000) });
}

async function callGoogle(
  record: JsonObject,
  parsed: JsonObject,
  model: string,
  apiKey: string,
  fetcher: FetchLike,
  baseUrl: string,
  thinkingBudget?: number,
): Promise<JsonObject> {
  const messages = buildMessages(record, parsed);
  const system = messages.filter(message => message.role === 'system').map(message => ({ text: message.content }));
  const contents = messages.filter(message => message.role !== 'system').map(message => ({ role: 'user', parts: [{ text: message.content }] }));
  const body = {
    systemInstruction: { parts: system }, contents,
    generationConfig: {
      temperature: 0, responseMimeType: 'application/json', responseSchema: googleResponseSchema,
      ...(Number.isInteger(thinkingBudget)
        ? { thinkingConfig: { thinkingBudget } }
        : {}),
    },
  };
  let lastError = 'unknown error';
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetchWithTimeout(fetcher, `${baseUrl}/models/${model}:generateContent`, {
        method: 'POST', headers: { 'x-goog-api-key': apiKey, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const raw = await response.text();
      if (!response.ok) {
        lastError = `HTTP ${response.status}: ${raw.slice(0, 500)}`;
        const fallback = classifyGoogleFailure(response.status, raw);
        if (fallback === 'provider_unavailable' && attempt === 0) continue;
        if (fallback) return resultFailure('google-ai-studio', model, lastError, raw, fallback);
        return resultFailure('google-ai-studio', model, lastError, raw);
      }
      const envelope = JSON.parse(raw);
      const content = (envelope.candidates?.[0]?.content?.parts ?? []).map((part: JsonObject) => part.text ?? '').join('');
      const payload = extractJsonObject(content);
      const invalid = validateGradingPayload(payload);
      if (invalid) return resultFailure('google-ai-studio', model, `model returned invalid grading JSON: ${invalid}`, content);
      const normalized = applyMaxMarksCap(payload!, resolveMaxMarks(record));
      const trustedInvalid = validateGradingPayload(normalized, record);
      if (trustedInvalid) return resultFailure('google-ai-studio', model, `model returned inconsistent grading JSON: ${trustedInvalid}`, content);
      return {
        schema_version: RESULT_SCHEMA_VERSION, ok: true, dry_run: false,
        model, provider: 'google-ai-studio',
        result: normalized,
        error: null, raw_response: content,
      };
    } catch (error) {
      lastError = `network error: ${error instanceof Error ? error.message : String(error)}`;
      if (attempt === 0) continue;
    }
  }
  return resultFailure('google-ai-studio', model, lastError, null, 'provider_unavailable');
}

async function callOpenRouter(
  record: JsonObject,
  parsed: JsonObject,
  apiKey: string,
  fetcher: FetchLike,
  baseUrl: string,
  model: string,
  providerOnly?: string[],
  providerSort?: string,
): Promise<JsonObject> {
  let lastError = 'unknown error';
  let lastRaw: string | null = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetchWithTimeout(fetcher, `${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json',
          'HTTP-Referer': 'https://cambridgeparser.com', 'X-Title': 'pseudocode-grading',
        },
        body: JSON.stringify({
          model, messages: buildMessages(record, parsed), temperature: 0,
          response_format: openRouterResponseFormat,
          provider: {
            require_parameters: true,
            ...(providerOnly?.length ? { only: providerOnly } : {}),
            ...(providerSort ? { sort: providerSort } : {}),
          },
        }),
      });
      lastRaw = await response.text();
      if (!response.ok) {
        lastError = `HTTP ${response.status}: ${lastRaw.slice(0, 500)}`;
        if ([429, 500, 502, 503].includes(response.status) && attempt === 0) continue;
        break;
      }
      const envelope = JSON.parse(lastRaw);
      const content = envelope.choices?.[0]?.message?.content;
      const payload = typeof content === 'string' ? extractJsonObject(content) : null;
      const invalid = validateGradingPayload(payload);
      if (invalid) return resultFailure('openrouter', model, `model returned invalid grading JSON: ${invalid}`, content ?? lastRaw);
      const normalized = applyMaxMarksCap(payload!, resolveMaxMarks(record));
      const trustedInvalid = validateGradingPayload(normalized, record);
      if (trustedInvalid) return resultFailure('openrouter', model, `model returned inconsistent grading JSON: ${trustedInvalid}`, content ?? lastRaw);
      return {
        schema_version: RESULT_SCHEMA_VERSION, ok: true, dry_run: false,
        model, provider: 'openrouter',
        result: normalized,
        error: null, raw_response: content,
      };
    } catch (error) {
      lastError = `network error: ${error instanceof Error ? error.message : String(error)}`;
      if (attempt === 0) continue;
    }
  }
  return resultFailure('openrouter', model, lastError, lastRaw);
}

async function rotatedModels(recordId: unknown, models: string[]): Promise<string[]> {
  if (models.length < 2) return models;
  const bytes = new TextEncoder().encode(String(recordId));
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  const offset = new DataView(digest.buffer).getUint32(0) % models.length;
  return [...models.slice(offset), ...models.slice(0, offset)];
}

export interface GradingEnvironment {
  googleKey?: string;
  googleModels?: string[];
  googleBaseUrl?: string;
  googleThinkingBudget?: number;
  openRouterKey?: string;
  openRouterModel?: string;
  openRouterBaseUrl?: string;
  openRouterProviderOnly?: string[];
  openRouterProviderSort?: string;
}

export async function gradeTrustedRecord(
  record: JsonObject,
  parsedAnswer: JsonObject,
  environment: GradingEnvironment,
  fetcher: FetchLike = fetch,
): Promise<JsonObject> {
  const attempts: JsonObject[] = [];
  let lastGoogleFailure: JsonObject | null = null;
  if (environment.googleKey) {
    const models = await rotatedModels(record.id, environment.googleModels?.length
      ? environment.googleModels
      : DEFAULT_GOOGLE_MODELS);
    for (const model of models) {
      const result = await callGoogle(
        record, parsedAnswer, model, environment.googleKey, fetcher,
        environment.googleBaseUrl ?? 'https://generativelanguage.googleapis.com/v1beta',
        environment.googleThinkingBudget,
      );
      if (result.ok || !result.fallback_reason) {
        if (attempts.length) result.fallback_from = attempts.at(-1);
        return result;
      }
      attempts.push({ provider: result.provider, model, reason: result.fallback_reason, error: result.error });
      lastGoogleFailure = result;
      // an HTTP/network outage is provider-wide. Trying every configured
      // Google model would multiply latency and requests before reaching the
      // independent fallback without increasing the chance of success.
      if (result.fallback_reason === 'provider_unavailable') break;
    }
  }

  if (environment.openRouterKey) {
    const result = await callOpenRouter(
      record, parsedAnswer, environment.openRouterKey, fetcher,
      environment.openRouterBaseUrl ?? 'https://openrouter.ai/api/v1',
      environment.openRouterModel ?? DEFAULT_OPENROUTER_MODEL,
      environment.openRouterProviderOnly,
      environment.openRouterProviderSort,
    );
    if (attempts.length) {
      result.fallback_from = attempts.at(-1);
      result.fallback_chain = attempts;
    }
    return result;
  }

  if (lastGoogleFailure) {
    lastGoogleFailure.fallback_chain = attempts;
    return lastGoogleFailure;
  }

  return resultFailure(
    environment.googleKey ? 'google-ai-studio' : 'none',
    environment.googleModels?.[0] ?? 'none',
    'AI grading is not configured: set GOOGLE_AI_STUDIO_API_KEY (or OPENROUTER_API_KEY).',
    null,
  );
}
