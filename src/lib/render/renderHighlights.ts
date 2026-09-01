import type { Ref } from "vue";
import type { DocumentHighlights, PageHighlights, SegmentHighlights, OptionHighlights, Highlight } from "@/lib/highlights/highlightTypes";
import { markNeutral, selectOption } from "@/lib/highlights/selectOption";
import type { EventLogs } from "@/lib/utils/utilsTypes";

export function renderHighlights(highlightMode: Ref<"correct" | "eliminated">, eventLogs: EventLogs, highlights: DocumentHighlights, totalScale: Ref<number>, pageIndexes?: number[], readOnly?: Readonly<Ref<boolean>>) {

  const pdfViewer: HTMLIFrameElement = document.querySelector("#pdf-viewer") as HTMLIFrameElement;
  const viewer: Element | null | undefined = pdfViewer?.contentDocument?.querySelector(`#viewer`);

  for(let pageIndex = 0; pageIndex < highlights.length; pageIndex++) {

    if(pageIndexes && !pageIndexes.includes(pageIndex)) continue;

    const pageHighlights: PageHighlights = highlights[pageIndex]!;

    const pages = viewer?.querySelectorAll('.page');
    const page = pages?.[pageIndex]!;

    // BUG FIX - resizes stacked duplicate highlights.
    //
    // This function only ever created elements and appended them; nothing
    // removed the previous set. It is called again on every `scalechanging`
    // event, which pdf.js fires whenever the viewport changes - including when
    // DevTools opens. So each resize doubled the highlights, and because they
    // are translucent the overlap darkened.
    //
    // Re-rendering a page now replaces that page's highlights rather than
    // adding to them. Scoped to `page` so pages not being re-rendered keep
    // theirs, matching the pageIndexes filter above.
    page?.querySelectorAll('.highlight').forEach(el => el.remove());

    for(let segmentIndex = 0; segmentIndex < pageHighlights.length; segmentIndex++) {
      
      const segmentHighlights: SegmentHighlights = pageHighlights[segmentIndex]!;

      for (let optionIndex = 0; optionIndex < segmentHighlights.length; optionIndex++) {

        const optionHighlights: OptionHighlights = segmentHighlights[optionIndex]!;

        for(let itemIndex = 0; itemIndex < optionHighlights.length; itemIndex++) {

          const highlightItem: Highlight = optionHighlights[itemIndex]!;

          const x: number = highlightItem.x;
          const y: number = highlightItem.y;
          const x2: number = highlightItem.x2;
          const y2: number = highlightItem.y2;
          
          const scaledX = x * totalScale.value;
          const scaledY = y * totalScale.value;
          const scaledWidth = (x2 - x) * totalScale.value;
          const scaledHeight = (y2 - y) * totalScale.value;
        
          const highlightDiv = document.createElement("div");
          highlightDiv.classList.add("highlight")
          highlightDiv.style.left = `${scaledX}px`;
          highlightDiv.style.top = `${scaledY}px`; 
          highlightDiv.style.width = `${scaledWidth}px`;
          highlightDiv.style.height = `${scaledHeight}px`;
        
          markNeutral(highlightDiv)

          page.appendChild(highlightDiv);

          if (!highlights[pageIndex]) highlights[pageIndex] = [];
          if (!highlights[pageIndex]![segmentIndex]) highlights[pageIndex]![segmentIndex] = [];
          if (!highlights[pageIndex]![segmentIndex]![optionIndex]) highlights[pageIndex]![segmentIndex]![optionIndex] = [];

          highlights[pageIndex]![segmentIndex]![optionIndex]![itemIndex]!.el = highlightDiv;

          highlightDiv.addEventListener('click', () => {
            // completed attempts remain scrollable in review mode, but their
            // answers must not be mutable or a second finish can rewrite history.
            if (readOnly?.value) return;
            const groupHighlights = highlights[pageIndex]![segmentIndex]![optionIndex]!
              .map(h => h.el)
              .filter(el => el !== null && el !== undefined);
            if(groupHighlights) {
              selectOption(highlightMode, eventLogs, pageIndex, segmentIndex, optionIndex, highlights, groupHighlights)
            }
          });
        }
      }
    }
  }
}
