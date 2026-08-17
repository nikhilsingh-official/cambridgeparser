import type { DocumentOptionsText, PageOptionsText, SegmentOptionsText, OptionText, textbox } from "../pdf";
import type { DocumentHighlights, OptionState } from "./highlightTypes";

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

          const x: number = highlightItem.x;
          const y: number = highlightItem.y + offset;
          const x2: number = highlightItem.x2;
          const y2: number = highlightItem.y2 + offset;
          const state: OptionState = "neutral";
          highlights[pageIndex]![segmentIndex]![optionIndex]!.push({ x, y, x2, y2, state })
        }
      }
    }
  }

  return highlights

}