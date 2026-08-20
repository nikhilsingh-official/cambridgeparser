import { watch, type Ref } from "vue";
import { computeGlobalIndex } from "../utils/computeGlobalIndex";
import type { DocumentFocusAreas, PageFocusAreas } from "@/lib/focusAreas/focusAreasTypes";

export function renderFocusAreas(documentFocusAreas: DocumentFocusAreas, totalScale: Ref<number>, pageIndexes?: number[]) {

  const pdfViewer: HTMLIFrameElement = document.querySelector("#pdf-viewer") as HTMLIFrameElement;
  const viewer = pdfViewer?.contentDocument?.querySelector(`#viewer`) as HTMLElement;

  for(let pageIndex = 0; pageIndex < documentFocusAreas.length; pageIndex++) {

    if(pageIndexes && !pageIndexes.includes(pageIndex)) continue;

    const pageFocusAreas: PageFocusAreas | undefined = documentFocusAreas[pageIndex];
    if(!pageFocusAreas) continue;

    const pageElement: Element | null = viewer.querySelector(`[data-page-number="${pageIndex + 1}"]`);

    // BUG FIX - every resize appended ANOTHER set of focus areas over the
    // old ones. They are translucent green, so each overlap read as darker.
    //
    // Nothing here ever removed the previous elements, and MCQNav re-invokes
    // this on `scalechanging`, which pdf.js fires on any viewport change -
    // opening DevTools is enough. Re-rendering a page now replaces that page's
    // focus areas instead of adding to them.
    pageElement?.querySelectorAll('.focus-area').forEach(el => el.remove());

    // and stop the watchers those elements owned. See stopTimeWatcher in
    // focusAreasTypes.ts - these are created outside a component scope, so
    // without this they accumulate one per re-render, forever, each writing
    // into a node that has just been removed.
    for (const fa of pageFocusAreas) {
      fa.stopTimeWatcher?.();
      fa.stopTimeWatcher = undefined;
    }

    for(let segmentIndex = 0; segmentIndex < pageFocusAreas.length; segmentIndex++) {

      const questionNum = computeGlobalIndex(documentFocusAreas, pageIndex, segmentIndex);

      const focusArea = documentFocusAreas[pageIndex]![segmentIndex];
      if(!focusArea) continue;

      const focusAreaEl: HTMLElement = document.createElement("div");

      focusAreaEl.classList.add("focus-area");
      focusAreaEl.dataset.questionNumber = `${questionNum}`;
      focusAreaEl.style.top = `${focusArea.y * totalScale.value}px`;
      focusAreaEl.style.height = `${(focusArea.y2 - focusArea.y) * totalScale.value}px`;
      pageElement?.appendChild(focusAreaEl);

      const focusTimerArea = document.createElement("div");
      focusTimerArea.classList.add("focus-area-timer");

      focusAreaEl.appendChild(focusTimerArea);

      focusArea.el = focusAreaEl;

      focusTimerArea.innerText = formatTime(focusArea.time);

      function formatTime(seconds: number) {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
            
        const pad = (n: number) => n.toString().padStart(2, "0");
        return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
      }

      // keep the stop handles so the next render can dispose these.
      const stopTime = watch(
        () => focusArea.time,
        (newVal) => {
          focusTimerArea.innerText = formatTime(newVal);
        }
      );

      // `active` is toggled reactively by eventListenersInit as the reader
      // scrolls, but nothing propagated it to the DOM after the initial render -
      // so the highlighted "current question" was frozen on whichever question
      // happened to be active when the page was drawn. Now it follows.
      const applyActive = (isActive: boolean) => {
        focusAreaEl.classList.toggle('is-active', isActive);
        focusTimerArea.classList.toggle('timer-active', isActive);
      };
      applyActive(focusArea.active);
      const stopActive = watch(() => focusArea.active, applyActive);

      focusArea.stopTimeWatcher = () => { stopTime(); stopActive(); };
    }
  }
}