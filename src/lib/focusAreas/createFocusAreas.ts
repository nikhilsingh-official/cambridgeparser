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
      const firstText: textbox | undefined = text[0];
      const lastText: textbox | undefined = text[segment.segmentText.length - 1];

      if(!segment || !text || !firstText || !lastText) continue;
      const y: number = firstText.y - 5;

      const nextSegment: QuestionSegment | undefined = pageSegments[segmentIndex + 1];
      const nextFirstText: textbox | undefined = nextSegment?.segmentText[0];

      let y2: number;
      if (nextSegment?.segmentText?.length && nextFirstText) {
        const buffer = Math.min(12.5, (nextFirstText.y - lastText.y2) / 2);
        y2 = nextFirstText.y - buffer;
      } else {
        y2 = lastText.y2 + 12.5;
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