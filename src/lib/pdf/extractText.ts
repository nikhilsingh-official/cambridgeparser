import type { TextItem } from "pdfjs-dist/types/src/display/api";
import type { DocumentText, textbox } from "@/lib/pdf/pdfTypes";
import * as pdfjsLib from 'pdfjs-dist';

export async function extractText(pdf: pdfjsLib.PDFDocumentProxy): Promise<DocumentText> {
  let totalText: textbox[][] = [];

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const textContent = await page.getTextContent();
    const viewport = page.getViewport({ scale: 1 });

    const pageItems: textbox[] = [];

    for (const raw of textContent.items) {
      if (!("str" in raw) || raw.str.trim() === "") continue;

      const item = raw as TextItem;

      const tfm = pdfjsLib.Util.transform(viewport.transform, item.transform);
      const x = tfm[4];
      const yTop = tfm[5];

      const width = item.width;
      const height = item.height;

      pageItems.push({
        text: item.str,
        font: item.fontName,
        rawFontName: item.fontName,
        x,
        y: yTop - height,
        x2: x + width,
        y2: yTop,
        width,
        height,
        fontSize: item.height,
        transform: item.transform
      });
    }

    totalText.push(pageItems);
  }

  return totalText;
}
