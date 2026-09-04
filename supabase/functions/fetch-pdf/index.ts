import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import * as pdfjs from "npm:pdfjs-serverless";
// extracted so the production parser and golden-corpus audit share one implementation.
import { getAnswersFromPDF } from "./answerKey.ts";
// the Edge Function, not the browser, now owns the shared key write.
import { normalizeTrustedAnswerKey, sha256Hex } from "./trustedAnswerKey.ts";
// keep PDF bytes binary while returning metadata in the same invocation.
import { createFetchPdfResponse } from "./paperResponse.ts";

const ANSWER_KEY_PARSER_VERSION = 1;

// new hosted projects expose named secret keys as JSON; the legacy local
// stack exposes SUPABASE_SERVICE_ROLE_KEY. Both are server-only and bypass RLS.
function getServerKey(): string | null {
  const named = Deno.env.get('SUPABASE_SECRET_KEYS');
  if (named) {
    try {
      const parsed = JSON.parse(named) as Record<string, string>;
      if (parsed.default) return parsed.default;
    } catch {
      return null;
    }
  }
  return Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? null;
}

async function persistAnswerKey(
  paperId: string,
  sourceUrl: string,
  sourceSha256: string,
  answers: ReturnType<typeof normalizeTrustedAnswerKey>,
): Promise<{ persisted: boolean; error?: string }> {
  if (!answers) return { persisted: false, error: 'The mark scheme answer table was incomplete.' };
  const url = Deno.env.get('SUPABASE_URL');
  const key = getServerKey();
  if (!url || !key) return { persisted: false, error: 'Trusted database credentials are unavailable.' };

  const headers: Record<string, string> = {
    apikey: key,
    'Content-Type': 'application/json',
  };
  if (!key.startsWith('sb_secret_')) headers.Authorization = `Bearer ${key}`;
  const response = await fetch(`${url}/rest/v1/rpc/install_verified_answer_key`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      p_paper_id: paperId,
      p_source_url: sourceUrl,
      p_source_sha256: sourceSha256,
      p_parser_version: ANSWER_KEY_PARSER_VERSION,
      p_answers: answers,
    }),
  });
  return !response.ok
    ? { persisted: false, error: 'The verified answer key could not be saved.' }
    : { persisted: true };
}

const ALLOWED_HOSTNAMES = new Set([
  "pastpapers.papacambridge.com",
  "www.papacambridge.com",
  "www.gceguide.com",
  "gceguide.com",
  "papers.gceguide.xyz",
  "xtremepapers.xyz",
]);

function expandSchema(schema: string) {
  const parts = schema.split("_");
  if (parts.length !== 3) return null;
  const [code, session, paper] = parts;
  return [`${code}_${session}_qp_${paper}`, `${code}_${session}_ms_${paper}`];
}

function isValidSchema(schema: string) {
  return typeof schema === "string" &&
    /^\d+_[a-z]\d{2}_\d+$/.test(schema);
}

function getURLs(schema: string) {
  if (!schema) return [];
  const papa = `https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/${schema}.pdf`;
  return [papa];
}

async function fetchFirstPDF(urls: string[], fetchTimeoutMs = 10000) {
  for (const url of urls) {
    try {
      const parsed = new URL(url);
      if (!ALLOWED_HOSTNAMES.has(parsed.hostname)) {
        console.warn(`Skipping disallowed host: ${parsed.hostname}`);
        continue;
      }

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), fetchTimeoutMs);

      const resp = await fetch(url, {
        method: "GET",
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
          "Accept": "application/pdf,*/*;q=0.8"
        },
        signal: controller.signal
      });

      clearTimeout(timeout);

      if (!resp.ok) {
        console.info(`URL ${url} returned ${resp.status}`);
        continue;
      }

      const ct = resp.headers.get("content-type") || "";
      if (!ct.includes("pdf")) {
        console.info(`URL ${url} gave content-type ${ct}, skipping`);
        continue;
      }

      return { response: resp, url };
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        console.info(`Fetch timeout for ${url}`);
      } else {
        console.warn(`Fetch error for ${url}:`, err);
      }
      continue;
    }
  }
  return null;
}

Deno.serve(async (req: any) => {
  try {
    if (req.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers: { "Content-Type": "application/json" } });
    }

    const payload = await req.json().catch(() => null);
    const schema = payload?.schema;
    if (!schema || !isValidSchema(schema)) {
      return new Response(JSON.stringify({ error: 'Invalid or missing "schema" in request body' }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const [qpSchema, msSchema] = expandSchema(schema) || [];
    const qpResult = await fetchFirstPDF(getURLs(qpSchema));
    const msResult = await fetchFirstPDF(getURLs(msSchema));
    if(!qpResult || !msResult) {
      return new Response(JSON.stringify({ error: "PDF not found for the given schema" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const headers = new Headers();
    headers.set("Cache-Control", "public, max-age=3600, s-maxage=86400");

    headers.set("X-Source-URL", qpResult.url);

    const qpArrayBuffer = await qpResult.response.arrayBuffer();
    const msArrayBuffer = await msResult.response.arrayBuffer();
    // hash before PDF.js sees the buffer; some PDF runtimes transfer and
    // detach input buffers as an optimization.
    const markSchemeSha256 = await sha256Hex(msArrayBuffer);
    // inject the Edge runtime's PDF.js adapter into the shared extractor.
    const answers = await getAnswersFromPDF(pdfjs, msArrayBuffer);
    const trustedAnswers = normalizeTrustedAnswerKey(answers);
    const answerKey = await persistAnswerKey(
      schema, msResult.url, markSchemeSha256, trustedAnswers,
    );

    // multipart avoids expanding each PDF byte into a JSON number while
    // preserving the one-call PDF + marking metadata contract.
    return createFetchPdfResponse(schema, qpArrayBuffer, {
      answers,
      answerKey,
    }, headers);

  } catch (err) {
    console.error("Unhandled error:", err);
    return new Response(JSON.stringify({ error: "Internal server error" }), { status: 500, headers: { "Content-Type": "application/json" } });
  }
});
