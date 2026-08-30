import type { DocumentOptionsText, PageOptionsText, SegmentOptionsText, OptionText, textbox } from "../pdf";
import type { DocumentHighlights, OptionState } from "./highlightTypes";

// label-only parsing is deliberately used when PDF draw order cannot
// safely associate formula/table fragments. Expand those tiny glyphs into
// practical click targets without changing the visible option association.
const labelTargetWidth = 24;
const labelTargetHeight = 18;

export function createHighlights(options: DocumentOptionsText) {

  /*
  *@param startPage: the first page index from which highlights must be applied
  *@param endPage: the last page index to which highlights must be applied
  *@param defaultIndicator: if true, then startPage and endPage are disregarded, as the default is to highlight the entire PDF
  */
  

  const highlights: DocumentHighlights = []
  for (let pageIndex = 0; pageIndex < options.length; pageIndex++) {

    const pageOptions: PageOptionsText | undefined = options[pageIndex];
    if (!pageOptions) continue;
    if (!highlights[pageIndex]) highlights[pageIndex] = [];

    for (let segmentIndex = 0; segmentIndex < pageOptions.length; segmentIndex++) {

      const segmentOptions: SegmentOptionsText | undefined = pageOptions[segmentIndex];
      if (!segmentOptions) continue;
      if (!highlights[pageIndex]![segmentIndex]) highlights[pageIndex]![segmentIndex] = [];

      for (let optionIndex = 0; optionIndex < segmentOptions.length; optionIndex++) {

        const option: OptionText | undefined = segmentOptions[optionIndex];
        if (!option) continue;
        if (!highlights[pageIndex]![segmentIndex]![optionIndex]) highlights[pageIndex]![segmentIndex]![optionIndex] = [];

        for (let itemIndex = 0; itemIndex < option.length; itemIndex++) {
          const highlightItem: textbox | undefined = option[itemIndex]
          if (!highlightItem) continue;

          const offset = 4;

          // only expand a single A-D glyph. Text-bearing options retain
          // their exact boxes so highlights continue to follow visible prose.
          const isLabelOnly = option.length === 1 && /^[ABCD]$/.test(highlightItem.text.trim());
          const horizontalPadding = isLabelOnly
            ? Math.max(0, (labelTargetWidth - (highlightItem.x2 - highlightItem.x)) / 2)
            : 0;
          const verticalPadding = isLabelOnly
            ? Math.max(0, (labelTargetHeight - (highlightItem.y2 - highlightItem.y)) / 2)
            : 0;

          const x: number = highlightItem.x - horizontalPadding;
          const y: number = highlightItem.y + offset - verticalPadding;
          const x2: number = highlightItem.x2 + horizontalPadding;
          const y2: number = highlightItem.y2 + offset + verticalPadding;
          const state: OptionState = "neutral";
          highlights[pageIndex]![segmentIndex]![optionIndex]!.push({ x, y, x2, y2, state })
        }
      }
    }
  }

  return highlights

}
