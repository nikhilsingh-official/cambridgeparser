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

      watch(
        () => focusArea.time,
        (newVal) => {
          focusTimerArea.innerText = formatTime(newVal);
        }
      );


      if (focusArea.active) {
        focusTimerArea.classList.add('timer-active');
      }
    }
  }
}