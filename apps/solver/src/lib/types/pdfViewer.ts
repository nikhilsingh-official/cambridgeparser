// ==========================================================================
//
// Minimal type declarations for the VENDORED pdf.js viewer.
//
// public/web/viewer.html + public/build/pdf.js are pdf.js v3.2.146, dropped in
// as static assets. They expose `PDFViewerApplication` and `pdfjsLib` as
// globals on the iframe's window, and ship no type declarations - so every
// touch point was `(iframeWindow as any)` or `evt: any`.
//
// These interfaces cover ONLY the surface this app actually uses. They are
// deliberately narrow: the goal is to name the shape at the boundary so the
// code inside is checked, not to re-declare the whole pdf.js API.
//
// NOTE ON VERSIONS: the npm `pdfjs-dist` dependency is v5, while the vendored
// viewer is v3. They are used for different things (v5 for Util/OPS and types,
// v3 for the actual document in the iframe), so these declarations describe the
// v3 viewer and must not be confused with pdfjs-dist's own types.
// See docs/future_work.md for the version-mismatch risk this creates.
// ==========================================================================

import type { PDFDocumentProxy } from 'pdfjs-dist';

/** A single rendered page in the viewer's internal page list. */
export interface PdfPageView {
  /** The page's container element. Carries `data-loaded` once rendered. */
  div?: HTMLElement;
  id?: number;
}

/** The viewer component that owns scrolling, zoom and the page list. */
export interface PdfViewer {
  currentPageNumber: number;
  /** Internal, but the only way to reach per-page elements in v3. */
  _pages?: PdfPageView[];
}

/** One entry of `updateviewarea`'s visible-page list. */
export interface PdfVisiblePage {
  /** 1-based page number. */
  id: number;
}

/** Payload of the `pagechanging` event. */
export interface PdfPageChangingEvent {
  pageNumber: number;
}

/** Payload of the `updateviewarea` event. */
export interface PdfUpdateViewAreaEvent {
  location?: {
    visiblePages?: PdfVisiblePage[];
  };
}

/** Payload of the `pagesloaded` event. */
export interface PdfPagesLoadedEvent {
  pagesCount: number;
}

/**
 * pdf.js's internal pub/sub. Typed as an overload set rather than a generic
 * `(name: string, cb: (evt: any) => void)` so each handler's payload is known.
 */
export interface PdfEventBus {
  on(name: 'pagesinit', handler: () => void): void;
  on(name: 'pagesloaded', handler: (evt: PdfPagesLoadedEvent) => void): void;
  on(name: 'pagechanging', handler: (evt: PdfPageChangingEvent) => void): void;
  on(name: 'updateviewarea', handler: (evt: PdfUpdateViewAreaEvent) => void): void;
  /** Fires when the user zooms. Carries no payload this app uses. */
  on(name: 'scalechanging', handler: () => void): void;
  off(name: string, handler: (...args: unknown[]) => void): void;
  /** The app re-fires 'pagesinit' itself once extraction has finished. */
  dispatch(name: string, payload?: Record<string, unknown>): void;
}

/** The global the vendored viewer publishes on its window. */
export interface PDFViewerApplication {
  /** Resolves once the viewer has booted. Awaited to avoid a race. */
  initializedPromise: Promise<void>;
  pdfViewer: PdfViewer;
  eventBus: PdfEventBus;
}

/**
 * The iframe's window, with the two globals the vendored viewer adds.
 * `pdfjsLib` is left loosely typed on purpose: it is the v3 library, not the
 * v5 one the rest of the app imports, so borrowing pdfjs-dist's types here
 * would assert a compatibility that has not been verified.
 */
export interface PdfViewerWindow extends Window {
  PDFViewerApplication: PDFViewerApplication;
  pdfjsLib: {
    // The return is declared as pdfjs-dist's PDFDocumentProxy because that is
    // what the rest of the pipeline (extractText, getOptions) consumes. Note
    // this asserts a v3 document satisfies a v5 type - true for the small
    // surface used here (getPage/getTextContent/getOperatorList/numPages), but
    // see the version-mismatch note in docs/future_work.md.
    getDocument(src: Uint8Array | { data: Uint8Array }): { promise: Promise<PDFDocumentProxy> };
  };
}

/** Narrowing helper for the `iframe.contentWindow` handoff. */
export function asPdfViewerWindow(win: Window): PdfViewerWindow {
  return win as PdfViewerWindow;
}
