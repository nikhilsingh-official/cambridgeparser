import {
  OPS,
  type PDFDocumentProxy
} from "pdfjs-dist";

import type { GraphicsItem, DocumentGraphics } from "./pdfTypes";

export async function extractGraphics(pdf: PDFDocumentProxy): Promise<DocumentGraphics> {
  const allPages: DocumentGraphics = [];

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const opList = await page.getOperatorList();

    const items: GraphicsItem[] = [];

    for (let j = 0; j < opList.fnArray.length; j++) {
      const fnId = opList.fnArray[j];
      const args = Array.isArray(opList.argsArray[j])
        ? opList.argsArray[j]
        : Object.values(opList.argsArray[j] ?? {});

      if(!fnId) continue;

      let name: string | undefined = undefined;

      if (
        fnId === OPS.paintImageXObject ||
        fnId === OPS.paintXObject ||
        fnId === OPS.paintFormXObjectEnd || 
        fnId === OPS.paintFormXObjectBegin
      ) {
        name = args?.[0];
      }

      items.push({ fnId, args, name });
    }

    allPages.push(items);
  }

  return allPages;
}