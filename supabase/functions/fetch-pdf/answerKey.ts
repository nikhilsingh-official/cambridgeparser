// ==========================================================================
//
// Mark-scheme table extraction shared by the Edge Function and corpus audit.
// The PDF.js implementation is injected so Deno can use pdfjs-serverless while
// the local audit runs the exact same algorithm in Node.
// ==========================================================================

export interface AnswerTableRow {
  question: number;
  answer: string;
  marks: string;
  page: number;
  y: number;
}

interface PositionedAnswerRow extends AnswerTableRow {
  qX: number;
  aX: number;
  mX: number;
}

interface PdfTextItem {
  str: string;
  transform: number[];
}

interface PdfPage {
  getTextContent(): Promise<{ items: Array<PdfTextItem | Record<string, unknown>> }>;
}

interface PdfDocument {
  numPages: number;
  getPage(pageNumber: number): Promise<PdfPage>;
}

export interface ServerPdfJs {
  getDocument(options: { data: ArrayBuffer }): { promise: Promise<PdfDocument> };
}

export async function getAnswersFromPDF(
  pdfjs: ServerPdfJs,
  arrayBuffer: ArrayBuffer,
  xLeeway = 5,
  yLeeway = 2,
): Promise<AnswerTableRow[] | null> {
  const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
  const pdf = await loadingTask.promise;

  let allItems: Array<{ text: string; x: number; y: number; page: number }> = [];

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const content = await page.getTextContent();
    content.items.forEach((raw) => {
      if (!('str' in raw) || !('transform' in raw)) return;
      const item = raw as PdfTextItem;
      allItems.push({
        text: item.str,
        x: item.transform[4] ?? 0,
        y: item.transform[5] ?? 0,
        page: pageNum,
      });
    });
  }

  if (allItems.length === 0) return null;

  allItems.sort((a, b) => a.page - b.page || b.y - a.y || a.x - b.x);
  allItems = allItems.filter((item) => {
    if (!item.text) return false;
    return item.text.replace(/[\s\u00A0\u200B\u200C\u200D]/g, '') !== '';
  });

  const rows: PositionedAnswerRow[] = [];
  let tableStarted = false;

  for (let i = 0; i < allItems.length; i++) {
    const item = allItems[i]!;

    if (!tableStarted && /Question/i.test(item.text)) {
      const sameRow = allItems.filter(
        (candidate) => Math.abs(candidate.y - item.y) < yLeeway && candidate.page === item.page,
      );
      const texts = sameRow.map((candidate) => candidate.text.toLowerCase());
      if (texts.includes('question') && texts.includes('answer') && texts.includes('marks')) {
        tableStarted = true;
        i += sameRow.length - 1;
        continue;
      }
    }

    if (!tableStarted) continue;

    const rowItems = allItems.filter(
      (candidate) =>
        candidate.page === item.page
        && Math.abs(candidate.y - item.y) < yLeeway
        && !rows.some((row) => row.y === candidate.y && row.page === candidate.page),
    );
    if (rowItems.length !== 3) continue;

    rowItems.sort((a, b) => a.x - b.x);
    if (rows.length > 0) {
      const previous = rows[rows.length - 1]!;
      const columnX = rowItems.map((candidate) => candidate.x);
      const previousX = [previous.qX, previous.aX, previous.mX];
      if (!columnX.every((x, column) => Math.abs(x - previousX[column]!) <= xLeeway)) continue;
    }

    rows.push({
      question: Number.parseInt(rowItems[0]!.text, 10) || -1,
      answer: rowItems[1]!.text,
      marks: rowItems[2]!.text,
      page: rowItems[0]!.page,
      y: rowItems[0]!.y,
      qX: rowItems[0]!.x,
      aX: rowItems[1]!.x,
      mX: rowItems[2]!.x,
    });
    i += rowItems.length - 1;
  }

  if (rows.length === 0) return null;

  const cleanRows: AnswerTableRow[] = [];
  let expectedQuestion = 1;
  for (const row of rows) {
    const question = Number.parseInt(String(row.question), 10);
    if (Number.isNaN(question)) continue;
    if (question === expectedQuestion) {
      cleanRows.push(row);
      expectedQuestion++;
    } else if (question > expectedQuestion) {
      cleanRows.push(row);
      expectedQuestion = question + 1;
    }
  }

  return cleanRows.length > 0 ? cleanRows : null;
}
