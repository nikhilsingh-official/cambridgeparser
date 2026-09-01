import type { Ref } from "vue";
// switched to the typed focus-area constructor. logFocusArea has no
// `option` parameter at all, which is what the five `undefined` arguments
// below were standing in for.
import { logFocusArea } from "../utils/addEventLog";
import { FocusAreaAction } from "@/lib/types/enums";
import type { EventLogs } from "../utils/utilsTypes";
import type { DocumentFocusAreas, FocusArea } from "./focusAreasTypes";
import { throttle } from "../utils/throttle";

export function eventListenersInit(
  documentFocusAreas: DocumentFocusAreas,
  totalScale: Ref<number>,
  eventLogs: EventLogs
) {
  const pdfViewer = document.querySelector("#pdf-viewer") as HTMLIFrameElement | null;
  const doc = pdfViewer?.contentDocument;
  if (!doc) return;

  const viewer = doc.querySelector("#viewer") as HTMLElement | null;
  if (!viewer) return;

  const lastHoverPerPage = new Map<number, FocusArea | null>();

  const pageIndexFromElement = (el: HTMLElement | null) =>
    el ? parseInt(el.dataset.pageNumber ?? "0", 10) - 1 : -1;

  const eventYToPageUnits = (evt: MouseEvent, pageEl: HTMLElement) => {
    const rect = pageEl.getBoundingClientRect();
    const yPixels = evt.clientY - rect.top;
    const scale = totalScale.value || 1;
    return yPixels / scale;
  };

  viewer.addEventListener("click", (ev) => {
    const e = ev as MouseEvent;
    const target = (e.target as HTMLElement) || null;
    const pageEl = target?.closest(".page") as HTMLElement | null;
    if (!pageEl) return;

    const pageIndex = pageIndexFromElement(pageEl);
    if (pageIndex < 0) return;

    const pageFocusAreas = documentFocusAreas[pageIndex];
    if (!pageFocusAreas) return;

    const y = eventYToPageUnits(e, pageEl);

    const current = pageFocusAreas.find((f) => y >= f.y && y <= f.y2) ?? null;
    if (!current) return;

    const previousActive = documentFocusAreas.flat().find((f) => f.active);
    if (previousActive && previousActive !== current) previousActive.active = false;

    current.active = true;
    logFocusArea(eventLogs, FocusAreaAction.UserClick, current.questionNumber);
  });

  function handleMouseMove(e: MouseEvent) {
    const target = e.target as HTMLElement | null;
    const pageEl = target?.closest(".page") as HTMLElement | null;
    if (!pageEl) return;

    const pageIndex = pageIndexFromElement(pageEl);
    if (pageIndex < 0) return;

    const pageFocusAreas = documentFocusAreas[pageIndex];
    const last = lastHoverPerPage.get(pageIndex) ?? null;

    if (!pageFocusAreas) {
      if (last) {
        logFocusArea(eventLogs, FocusAreaAction.UserHoveredOutPage, last.questionNumber);
        lastHoverPerPage.set(pageIndex, null);
      }
      return;
    }

    const y = eventYToPageUnits(e, pageEl);
    const current = pageFocusAreas.find((f) => f.y <= y && f.y2 >= y) ?? null;

    if (last && current !== last) {
      logFocusArea(eventLogs, FocusAreaAction.UserHoveredOutPage, last.questionNumber);
    }

    if (current && current !== last) {
      logFocusArea(eventLogs, FocusAreaAction.UserHoveredIn, current.questionNumber);
    }

    lastHoverPerPage.set(pageIndex, current);
  }

  const throttledMouseMove = throttle(handleMouseMove, 12);
  viewer.addEventListener("mousemove", throttledMouseMove);

  viewer.addEventListener("mouseleave", () => {
    for (const [_pageIndex, last] of lastHoverPerPage.entries()) {
      if (last) {
        logFocusArea(eventLogs, FocusAreaAction.UserHoveredOutPage, last.questionNumber);
      }
    }
    lastHoverPerPage.clear();
  });
}
