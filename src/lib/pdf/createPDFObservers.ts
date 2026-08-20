import type { Ref } from "vue";
import type { DocumentButtonTracks } from "../buttons";
import type { DocumentFocusAreas } from "../focusAreas";
import type { DocumentHighlights } from "../highlights";
import { renderFocusAreas } from "../render/renderFocusAreas";
import { renderHighlights } from "../render/renderHighlights";
import { renderTracks } from "../render/renderTracks";
import type { EventLogs, HighlightMode } from "../utils/utilsTypes";
// the vendored pdf.js viewer ships no types; these name the small
// surface this function touches. See @/lib/types/pdfViewer.
import type {
  PdfPageChangingEvent,
  PdfUpdateViewAreaEvent,
  PdfViewerWindow,
} from "@/lib/types/pdfViewer";

export function createPDFObservers(
  highlightMode: Ref<HighlightMode>,
  eventLogs: EventLogs,
  totalScale: Ref<number>,
  highlights: DocumentHighlights,
  focusAreas: DocumentFocusAreas,
  tracks: DocumentButtonTracks,
  // was `win: any`.
  win: PdfViewerWindow
) {

  const { pdfViewer, eventBus } = win.PDFViewerApplication;

  let lastVisiblePages: number[] = [];

  function renderForPages(pages: number[]) {
    if (!pages.length) return;

    // argument order was (…, pages, totalScale) but renderHighlights takes
    // (…, totalScale, pageIndexes) in this version - the two drifted apart when
    // the renderers were reworked and nothing caught it, because this whole
    // module is unreachable (no importer). Corrected to match the signature.
    renderHighlights(highlightMode, eventLogs, highlights, totalScale, pages);
    renderFocusAreas(focusAreas, totalScale, pages);
    renderTracks(tracks, pages, totalScale, eventLogs);
  }

  eventBus.on("pagesinit", () => {
    const current = pdfViewer.currentPageNumber - 1;
    lastVisiblePages = [current];
    renderForPages(lastVisiblePages);
  });

  eventBus.on("pagechanging", (evt: PdfPageChangingEvent) => {
    const pageIndex = evt.pageNumber - 1;
    lastVisiblePages = [pageIndex];
    renderForPages(lastVisiblePages);
  });

  eventBus.on("updateviewarea", (evt: PdfUpdateViewAreaEvent) => {
    const visible = evt.location?.visiblePages;
    if (!visible?.length) return;

    const pages = visible.map((p) => p.id - 1);
    lastVisiblePages = pages;
    renderForPages(pages);
  });

  console.log("PDF.js EventBus observers registered.");
}
