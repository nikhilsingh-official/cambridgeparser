import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import * as pdfjs from "npm:pdfjs-serverless";

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

interface TableRow {
  question: number;
  answer: string;
  marks: string;
  page: number;
  y: number;
}

interface ColumnStats {
  x: number;
  values: number[];
}

async function getAnswersFromPDF(arrayBuffer: ArrayBuffer, xLeeway = 5, yLeeway = 2): Promise<TableRow[] | null> {
  const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
  const pdf = await loadingTask.promise;

  let allItems: { text: string; x: number; y: number; page: number }[] = [];

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const content = await page.getTextContent();
    content.items.forEach((item: any) => {
      allItems.push({
        text: item.str,
        x: item.transform[4],
        y: item.transform[5],
        page: pageNum,
      });
    });
  }

  if (allItems.length === 0) {
    return null;
  }

  // Group items by approximate Y (rows)
  allItems.sort((a, b) => a.page - b.page || b.y - a.y || a.x - b.x);
  allItems = allItems.filter(item => {
    if (!item.text) return false; // ignore null/undefined
    // Remove all types of spaces and zero-width chars
    const normalized = item.text.replace(/[\s\u00A0\u200B\u200C\u200D]/g, '');
    return normalized !== '';
  });

  const rows: TableRow[] = [];
  let tableStarted = false;

  for (let i = 0; i < allItems.length; i++) {
    const item = allItems[i];

    if (!tableStarted && /Question/i.test(item.text)) {
      // Heuristic: look for Question / Answer / Marks in the same y row
      const sameRow = allItems.filter(it => Math.abs(it.y - item.y) < yLeeway && it.page === item.page);
      const texts = sameRow.map(it => it.text.toLowerCase());
      if (texts.includes("question") && texts.includes("answer") && texts.includes("marks")) {

        tableStarted = true;
        i += sameRow.length - 1; // skip header row
        continue;
      }
    }

    if (tableStarted) {
      // Try to find a row of exactly 3 items on this y
      const rowItems = allItems.filter(
        it =>
          it.page === item.page &&
          Math.abs(it.y - item.y) < yLeeway &&
          !rows.some(r => r.y === it.y && r.page === it.page)
      );

      if (rowItems.length !== 3) continue; // ignore incomplete rows

      if (rows.length > 0) {
        const prevRow = rows[rows.length - 1];
        const colX = [rowItems[0].x, rowItems[1].x, rowItems[2].x];
        const prevX = [prevRow.qX, prevRow.aX, prevRow.mX];

        if (!colX.every((x, i) => Math.abs(x - prevX[i]) <= xLeeway)) continue;
      }


      // Sort row left-to-right by x
      rowItems.sort((a, b) => a.x - b.x);

      rows.push({
        question: parseInt(rowItems[0].text) || -1,
        answer: rowItems[1].text,
        marks: rowItems[2].text,
        page: rowItems[0].page,
        y: rowItems[0].y,
        qX: rowItems[0].x,
        aX: rowItems[1].x,
        mX: rowItems[2].x
      });

      i += rowItems.length - 1;

    }
  }

  if (rows.length === 0) {
    return null;
  }

  // Validate sequential question numbers & remove outliers
  const cleanRows: TableRow[] = [];
  let expectedQ = 1;
  for (const r of rows) {
    const qNum = parseInt(r.question, 10);
    if (isNaN(qNum)) continue; // skip invalid
    if (qNum === expectedQ) {
      cleanRows.push(r);
      expectedQ++;
    } else if (qNum > expectedQ) {
      expectedQ = qNum + 1;
      cleanRows.push(r);
    }
  }


  
  return cleanRows.length > 0 ? cleanRows : null;
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
    headers.set("Content-Type", "application/json");
    headers.set("Content-Disposition", `inline; filename="${schema}.pdf"`);
    headers.set("Cache-Control", "public, max-age=3600, s-maxage=86400");

    headers.set("X-Source-URL", qpResult.url);

    const qpArrayBuffer = await qpResult.response.arrayBuffer();
    const msArrayBuffer = await msResult.response.arrayBuffer();
    const answers = await getAnswersFromPDF(msArrayBuffer);

    const body = {
      qp:  Array.from(new Uint8Array(qpArrayBuffer)),
      answers: answers
    }

    console.log(body)

    return new Response(JSON.stringify(body), {
      status: 200,
      headers
    });

  } catch (err) {
    console.error("Unhandled error:", err);
    return new Response(JSON.stringify({ error: "Internal server error" }), { status: 500, headers: { "Content-Type": "application/json" } });
  }
});