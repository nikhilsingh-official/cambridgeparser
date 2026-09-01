import { reactive } from "vue";
import type { SegmentedQuestions, PageSegments, QuestionSegment, textbox } from "../pdf";
import { computeGlobalIndex } from "../utils/computeGlobalIndex";
import type { DocumentFocusAreas, PageFocusAreas } from "./focusAreasTypes";

export function createFocusAreas(segmentedQuestions: SegmentedQuestions) {
  const pdfViewer: HTMLIFrameElement = document.querySelector("#pdf-viewer") as HTMLIFrameElement;
  const viewer = pdfViewer?.contentDocument?.querySelector(`#viewer`) as HTMLElement;

  const documentFocusAreas: DocumentFocusAreas = []

  for(let pageIndex = 0; pageIndex < segmentedQuestions.length; pageIndex++) {
    const pageSegments: PageSegments | undefined = segmentedQuestions[pageIndex];
    if(!pageSegments) continue;

    const pageFocusAreas: PageFocusAreas = []

    const pageElement: Element | null = viewer.querySelector(`[data-page-number="${pageIndex + 1}"]`);

    for (let segmentIndex = 0; segmentIndex < pageSegments.length; segmentIndex++) {

      const segment: QuestionSegment | undefined = pageSegments[segmentIndex];
      if(!segment) continue;

      const questionNum = computeGlobalIndex(segmentedQuestions, pageIndex, segmentIndex);

      if (pageElement?.querySelector(`.focus-area[data-question-number="${questionNum}"]`)) {
        continue;
      }

      const text: textbox[] = segment.segmentText;

      if(!segment || !text || !text.length) continue;
      // was `text[0].y` and `text[length - 1].y2`, which read the first and
      // last elements of the array as the question's top and bottom edges. The
      // array is in PDF content-stream order, not top-to-bottom order, so those
      // are whichever items the typesetter happened to draw first and last - on
      // a question with a diagram the last drawn label sits partway up the
      // question, and the box stopped short of the answer options by a median
      // of 88pt (worst 422pt) across the 52 papers measured. contentY /
      // contentY2 are the real extremes, computed in segmentQuestions.ts.
      const y: number = segment.contentY - 5;

      const nextSegment: QuestionSegment | undefined = pageSegments[segmentIndex + 1];

      let y2: number;
      if (nextSegment) {
        const buffer = Math.min(12.5, (nextSegment.contentY - segment.contentY2) / 2);
        y2 = nextSegment.contentY - buffer;
      } else {
        y2 = segment.contentY2 + 12.5;
      }

      pageFocusAreas.push(reactive({
        y,
        y2,
        time: 0,
        active: false,
        questionNumber: questionNum,
        el: undefined
      }));
    };

    documentFocusAreas.push(pageFocusAreas);
  };

  return documentFocusAreas;

}