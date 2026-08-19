import type { DocumentText } from './pdfTypes'

export function detectOptionFonts(totalText: DocumentText): { font: string; proportion: number; }[] {

  const totalByFont: Record<string, number> = {};
  const optionByFont: Record<string, number> = {};

  for (let pageIndex = 0; pageIndex < totalText.length; pageIndex++) {
    const pageText = totalText[pageIndex]!;

    for (let textIndex = 0; textIndex < pageText.length; textIndex++) {
      const textbox = pageText[textIndex]!;
      const font = textbox.font.trim();
      const text = textbox.text.trim();

      totalByFont[font] = (totalByFont[font] || 0) + 1;

      if (text === "A" || text === "B" || text === "C" || text === "D") {
        optionByFont[font] = (optionByFont[font] || 0) + 1;
      }
    }
  }

  const fontProportions = Object.keys(totalByFont).map(font => {
    const total = totalByFont[font]!;
    const optionCount = optionByFont[font] || 0;
    return {
      font,
      proportion: optionCount / total
    };
  });

  fontProportions.sort((a, b) => b.proportion - a.proportion);

  return fontProportions;
}