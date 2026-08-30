// textbox is used by the geometry-based page-furniture filters below.
import type { DocumentText, DocumentQuestionMarkers, SegmentedQuestions, PageText, PageSegments, textbox } from "@/lib/pdf/pdfTypes";

// page furniture - the header page number, the copyright line, "[Turn over"
// and the typesetter's internal paper code.
//
// WHY TEXT AND NOT POSITION. A margin threshold cannot do this. Measured over
// 52 papers: genuine option letters reach y2=776 while footer items start at
// y2=713, so the two overlap by 63pt and 192 real option letters sit BELOW the
// highest footer item. There is no horizontal line that separates them.
//
// The top-of-page number is the one case position does settle: the lowest
// question marker in the corpus sits at y=61, so nothing above y2=50 is content.
const furnitureTopY = 50;
const furnitureText = /©|\bUCLES\b|^\[\s*Turn(?:\s+over)?\s*$|^\d{2}_\d{4}_\d{2}_\d{4}_/i;

// Kerning splits a run into several text items - "[Turn over" arrives as
// "[Turn", "o", "ver" - and no pattern can recognise "ver". Anything sharing a
// line with a matched item is therefore furniture too. Safe because the
// footer sits ~22pt below the lowest option letter any of the 52 papers
// contains, so no content line is ever within tolerance of one.
const furnitureLineTolerance = 3;

function pageFurniture(pageText: PageText): Set<textbox> {
  const seeds = pageText.filter((item: textbox) =>
    item.y2 < furnitureTopY || furnitureText.test(item.text.trim()));
  if (seeds.length === 0) return new Set();
  return new Set(pageText.filter((item: textbox) =>
    seeds.some(seed => Math.abs(seed.y2 - item.y2) <= furnitureLineTolerance)));
}

export function segmentQuestions(totalText: DocumentText, question_numbers: DocumentQuestionMarkers): SegmentedQuestions {

  let segmentedQuestions: SegmentedQuestions = [];

  for (let pageIndex = 0; pageIndex < totalText.length; pageIndex++) {

    const textSet = totalText[pageIndex]
    if(!textSet) continue;
    const pageText: PageText = textSet;

    const questionNumsOnPage = question_numbers[pageIndex];
    if (!questionNumsOnPage) continue;

    let pageSegments: PageSegments = [];

    // computed once per page rather than per question; the seeds are the same
    // for every segment on it.
    const furniture = pageFurniture(pageText);

    for (let i = 0; i < questionNumsOnPage.length; i++) {
      const current = questionNumsOnPage[i];
      const next = questionNumsOnPage[i + 1];

      if (!current) continue;
      // PDF content-stream indices are draw order, not visual reading
      // order. A later question's stem can be drawn before the preceding
      // option labels, while diagram labels are often drawn last. Segment by
      // the question markers' vertical geometry so neither case crosses a
      // question boundary. Three points groups boxes sharing the marker line
      // despite small font-metric differences.
      const startBoundary = current.y - 3;
      const endBoundary = next ? next.y - 3 : Infinity;
      const questionSegment = pageText
        .filter((item: textbox) =>
          item.y >= startBoundary
          && item.y < endBoundary
          && !furniture.has(item));
      if (questionSegment.length === 0) continue;

      // was `questionSegment.sort(...)`, which sorts IN PLACE - and this
      // is the same array that becomes segmentText below, so the page's last
      // question was stored in y-order instead of reading order. getOptions()
      // slices that array by index to find each option's text, so reordering
      // it silently moved the option boundaries. Reduced instead: a maximum
      // needs no sort, and nothing is mutated.
      const contentY: number = questionSegment.reduce(
        (lowest, item) => Math.min(lowest, item.y), Infinity);
      const contentY2: number = questionSegment.reduce(
        (highest, item) => Math.max(highest, item.y2), -Infinity);

      // was `(next.y - current.y2) / 2`, which is half the GAP between two
      // questions being used as an absolute coordinate - and the intended
      // `+ 5` sat after a semicolon, so it was a discarded expression that
      // never applied. The midpoint of the gap is what this wanted.
      const startY: number = contentY;
      const endY: number = next ? (next.y + contentY2) / 2 : contentY2 + 5;

      const averageY: number = (startY + endY) / 2;

      pageSegments.push({ segmentText: questionSegment, averageY, contentY, contentY2 });
    }

    segmentedQuestions.push(pageSegments);
  }

  return segmentedQuestions

}
