import type { Ref } from "vue";
import type { DocumentButtonTracks } from "../buttons";
import type { DocumentFocusAreas } from "../focusAreas";
import type { DocumentHighlights } from "../highlights";
import { renderFocusAreas } from "../render/renderFocusAreas";
import { renderHighlights } from "../render/renderHighlights";
import { renderTracks } from "../render/renderTracks";
import type { EventLogs, HighlightMode } from "../utils/utilsTypes";

export function createPDFObservers(
  highlightMode: Ref<HighlightMode>,
  eventLogs: EventLogs,
  totalScale: Ref<number>,
  highlights: DocumentHighlights,
  focusAreas: DocumentFocusAreas,
  tracks: DocumentButtonTracks,
  win: any
) {

  const { pdfViewer, eventBus } = win.PDFViewerApplication;

  let lastVisiblePages: number[] = [];

  function renderForPages(pages: number[]) {
    if (!pages.length) return;

    renderHighlights(highlightMode, eventLogs, highlights, pages, totalScale);
    renderFocusAreas(focusAreas, totalScale, pages);
    renderTracks(tracks, pages, totalScale, eventLogs);
  }

  eventBus.on("pagesinit", () => {
    const current = pdfViewer.currentPageNumber - 1;
    lastVisiblePages = [current];
    renderForPages(lastVisiblePages);
  });

  eventBus.on("pagechanging", (evt: any) => {
    const pageIndex = evt.pageNumber - 1;
    lastVisiblePages = [pageIndex];
    renderForPages(lastVisiblePages);
  });

  eventBus.on("updateviewarea", (evt: any) => {
    const visible = evt.location?.visiblePages;
    if (!visible?.length) return;

    const pages = visible.map((p: any) => p.id - 1);
    lastVisiblePages = pages;
    renderForPages(pages);
  });

  console.log("PDF.js EventBus observers registered.");
}
