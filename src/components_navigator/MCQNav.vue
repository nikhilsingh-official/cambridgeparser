<script setup lang="ts">
import LoadingScreen from './LoadingScreen.vue';
// the results screen shown when the attempt ends.
import EndScreen from './EndScreen.vue';
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import TopBar from './TopBar.vue';
import SideWindow from './SideWindow.vue';
import ToolsContainer from './ToolsContainer.vue';
import { getShowStates } from './composable';
import BottomBar from './BottomBar.vue';
import { createKeydownHandlers } from '@/lib/utils/keydownListeners';
import type { TableRow } from '@/lib/processing/processingTypes';
import { useAuthStore, supabase } from '@/stores/useAuth';
import { type DocumentFocusAreas, createFocusAreas, eventListenersInit, startFocusAreaTimer } from '@/lib/focusAreas';
import { createHighlights, type DocumentHighlights } from '@/lib/highlights';
import { extractText, identifyQuestionNumbers, segmentQuestions, getOptions } from '@/lib/pdf';
// extracted so its idempotence can be unit-tested without a DOM.
import { stripInlineBackground } from '@/lib/pdf/stripInlineBackground';
import type { EventLogs } from '@/lib/utils/utilsTypes';
import { enrichAnalytics } from '@/lib/processing/enrichAnalytics';
// reactive per-question state behind the Overview panel.
import { resetExamState, seedQuestions } from '@/lib/state/examState';
import { computeGlobalIndex } from '@/lib/utils/computeGlobalIndex';
import { getQuestionsAnalytics } from '@/lib/processing/getQuestionAnalytics';
// direct table writers are replaced by one transactional completion RPC.
import { startExamAttempt, abandonExamAttempt, finalizeExamAttempt } from '@/lib/supabase/pushToExamTable';
// exam-relative event timing, and the shared session the flag buttons read.
import { setEventEpoch } from '@/lib/utils/addEventLog';
// the attempt_status values, so 'completed'/'abandoned' are not bare strings.
import { registerExamSession, registerExamHighlights, getHighlightMode } from './composable';
import router from '@/router/router';
// types for the vendored pdf.js viewer and the fetch-pdf contract.
import { asPdfViewerWindow, type PdfPageView } from '@/lib/types/pdfViewer';
// drives the paper's dark mode and the mirrored token values.
import { currentTheme, isLightTheme } from '@/lib/theme';
import type { FetchPdfResponse, LoadedPaper } from '@/lib/types/fetchPdf';
// local summary computation for the end screen.
import { buildExamSummary, type ExamSummary } from '@/lib/types/examSummary';
import { renderHighlights } from '@/lib/render/renderHighlights';
import { renderFocusAreas } from '@/lib/render/renderFocusAreas';
// fail closed when the edge function returns a partial or malformed key.
import { validateAnswerKey } from '@/lib/pdf/validateAnswerKey';

const { showOverview } = getShowStates();
  
let perfStart: number | null;
const examLoaded = ref(false);
const examStarted = ref(false);
// drives the real distraction-free layout rather than a local switch that
// nothing outside ZenMode could observe.
const zenMode = ref(false);
// the paper failed to load. Added because the Paper Browser is now the only
// way into the solver, so a student can pick any catalogue combination - and
// fetch-pdf 404s when that series/variant was never sat. setup() previously ran
// unawaited and uncaught, so a 404 left the loading screen cycling
// "Preparing the PDF..." forever with no way to tell it had failed.
const loadError = ref<string | null>(null);
// a paper can still be used locally when its verified key cannot persist,
// but that session must be labelled and excluded from authoritative history.
const practiceWarning = ref<string | null>(null);

const iframeRef = ref<HTMLIFrameElement | null>(null);
let observer: MutationObserver | null = null;

const props = defineProps<{
  schema: string
}>();

// was a local `ref("correct")` that only MCQNav and the keybinds could see.
// It now comes from the shared session so the Tools slider and the bottom-bar
// indicator track the same value - see the note in composable.ts.
const { highlightMode } = getHighlightMode();
let eventLogs: EventLogs = [];
let highlights: DocumentHighlights = [];
let focusAreas: DocumentFocusAreas = [];
const totalScale = ref(1);
// resources created outside Vue's component scope need explicit teardown.
let stopFocusTimer: (() => void) | null = null;
let pdfObjectUrl: string | null = null;
// retain the exact iframe callback so teardown can remove it if the route
// changes before the one-shot load event fires.
let iframeLoadHandler: (() => void) | null = null;

const { register, unregister } = createKeydownHandlers(highlightMode);
const { session } = useAuthStore();

// `dateStart` removed - it existed only to back-date started_at in the old
// one-shot write. startExamAttempt() now stamps started_at when the attempt
// actually opens, so nothing consumed it any more.
let answers: TableRow[] | null = null;
// held for the duration of the attempt - opened in startExam(), written to
// throughout, closed in endExam().
let examAttemptId: string | null = null;
let completionId: string | null = null;
let lastCompletion: { durationMs: number; questions: ReturnType<typeof enrichAnalytics> } | null = null;

// end-screen state. `examFinished` drives the overlay; `summary` is null
// until endExam() has marked the paper, which is what shows the interim
// "Marking your paper..." state.
const examFinished = ref(false);
const summary = ref<ExamSummary | null>(null);
const saving = ref(false);
const saveError = ref<string | null>(null);
// review mode permits PDF scrolling/zooming but freezes attempt state.
const reviewOnly = ref(false);
// distinguishes a fully persisted attempt from the in-progress row.
const attemptSaved = ref(false);

// the fetch-pdf edge function's response had no type at all - `answers`
// was `any`, so the mark-scheme rows flowed untyped into getQuestionsAnalytics
// and persistence. FetchPdfResponse/LoadedPaper name that contract.
async function getPDF(): Promise<LoadedPaper> {

  const { data, error } = await supabase.functions.invoke("fetch-pdf", {
    body: {
      schema: props.schema
    }
  });

  if (error) {
    console.error("fetch-pdf error:", error);
    throw error;
  }

  // `functions.invoke` returns `any`, so the response is named here at the
  // boundary. Everything downstream of this line is typed.
  const body = data as FetchPdfResponse;
  const answers = validateAnswerKey(body.answers);
  if (!answers) throw new Error('The mark scheme did not contain a complete answer key');

  const pdfBytes = new Uint8Array(
    Array.isArray(body.qp)
      ? body.qp
      : Object.values(body.qp)
  );

  const pdfBlob = new Blob([pdfBytes], {
    type: "application/pdf"
  });

  const pdfUrl = URL.createObjectURL(pdfBlob);

  return {
    answers,
    pdfBytes,
    pdfUrl,
    answerKeyPersisted: body.answerKey?.persisted === true,
    answerKeyError: body.answerKey?.error,
  };
}


// the attempt row is now opened here rather than at endExam(), so an
// abandoned paper is still recorded and started_at is an observation instead of
// a value the client back-dates at the end.
async function startExam() {
  // a fresh attempt begins mutable and is not fully saved yet.
  reviewOnly.value = false;
  attemptSaved.value = false;
  perfStart = performance.now();
  // anchor event timing to exam start so stored elapsed_ms is meaningful.
  setEventEpoch(perfStart);
  // hand the event log and focus areas to the shared exam session so the
  // flag buttons in ToolsContainer can log against the focused question.
  registerExamSession(eventLogs, focusAreas);
  examStarted.value = true;

  if (practiceWarning.value) return;

  try {
    // `session` is Session | null - typing startExamAttempt surfaced that it
    // was being passed unchecked. It is also captured once at setup (Pinia
    // destructuring is not reactive), so a session that arrives later leaves
    // this null; see docs/future_work.md.
    if (!session) throw new Error('No Supabase session; attempt not persisted');
    examAttemptId = await startExamAttempt(supabase, props, session, answers?.length);
  } catch (err) {
    // a failed open must not block the student from sitting the paper. The
    // attempt simply is not persisted; endExam() detects the null id.
    console.error('startExam: could not open attempt', err);
  }
}

async function endExam() {
  // reopening results after review must not serialize the closed attempt a
  // second time. This is a persistence guard as well as a UI guard.
  if (attemptSaved.value) {
    examFinished.value = true;
    return;
  }

  // the results screen goes up immediately, before any network work, so
  // the candidate is never left looking at the paper wondering if it worked.
  examFinished.value = true;
  reviewOnly.value = true;
  saving.value = true;
  saveError.value = null;

  try {
    // BUG FIX. This was a bare `return`, which left summary null and
    // saveError null - so the end screen sat on "Marking your paper..."
    // forever with no indication that anything had gone wrong. Without the
    // mark scheme there is nothing to mark against, so say so.
    if (!answers) {
      saveError.value = 'Mark scheme unavailable - the paper could not be marked.';
      return;
    }
    const questionsData = getQuestionsAnalytics(highlights, focusAreas, answers);
    const enrichedData = enrichAnalytics(questionsData, eventLogs);

    if (perfStart == null) throw new Error("Exam hasn't started");

    const elapsedMs = Math.round(performance.now() - perfStart);

    // marked locally from data already in hand, so the score paints even if
    // every write below fails. The database remains authoritative.
    //
    // BUG FIX: this was passed `questionsData` (pre-enrichment). explorationDepth
    // is produced by enrichAnalytics, not getQuestionsAnalytics, so it was always
    // undefined here - the guess rule's `(q.explorationDepth ?? 0) <= 1` term was
    // therefore always true and the heuristic silently collapsed to "fast" alone.
    // That both over-reported lucky guesses and diverged from v_question_flags,
    // which uses the real stored exploration_depth. enrichAnalytics returns
    // `{ ...q, ... }`, so enrichedData is a strict superset and nothing is lost.
    summary.value = buildExamSummary(props.schema, enrichedData, answers, elapsedMs);
    lastCompletion = { durationMs: elapsedMs, questions: enrichedData };

    if (practiceWarning.value) {
      saveError.value = practiceWarning.value;
      return;
    }

    // fall back to opening one now if startExam() could not.
    if (!examAttemptId) {
      // same null guard as in startExam().
      if (!session) throw new Error('No Supabase session; attempt not persisted');
      examAttemptId = await startExamAttempt(supabase, props, session, answers.length);
    }

    // keep one idempotency key across retries. A response lost after the
    // transaction commits can therefore be retried without duplicate rows.
    completionId ??= crypto.randomUUID();
    await finalizeExamAttempt(
      supabase, examAttemptId, completionId, elapsedMs, enrichedData, eventLogs,
    );
    // set only after every write and the final status update succeed.
    attemptSaved.value = true;

    return { examAttemptId, insertedCount: enrichedData.length };
  } catch (err) {
    // a persistence failure must not hide the result. The screen stays up
    // and says so; it no longer rethrows, which would have left the overlay in
    // its indeterminate state.
    console.error('endExam failed', err);
    saveError.value = err instanceof Error ? err.message : String(err);
  } finally {
    saving.value = false;
  }
}

// end-screen actions.
function goToDashboard() {
  router.push('/');
}

// dismisses the overlay and returns to the paper, read-only - the attempt
// is already closed, so nothing further is recorded.
function reviewPaper() {
  examFinished.value = false;
}

// retry the frozen payload with the same completion id. Rebuilding it from
// review-mode UI would make a retry a different submission.
async function retrySave() {
  if (!examAttemptId || !completionId || !lastCompletion || attemptSaved.value) return;
  saving.value = true;
  saveError.value = null;
  try {
    await finalizeExamAttempt(
      supabase,
      examAttemptId,
      completionId,
      lastCompletion.durationMs,
      lastCompletion.questions,
      eventLogs,
    );
    attemptSaved.value = true;
  } catch (err) {
    saveError.value = err instanceof Error ? err.message : String(err);
  } finally {
    saving.value = false;
  }
}

// NEW - closes an attempt the student walks away from.
//
// The lifecycle had only two of its three exits implemented: startExamAttempt()
// opened the row and finalizeExamAttempt() closed it on End Exam, but leaving the
// page mid-paper left status pinned at 'in_progress' forever. Those rows are
// indistinguishable from an exam still being sat, so every dashboard query has
// to either count half-finished papers or exclude live ones.
//
// Best-effort by nature: on a route change (below) the update reliably lands,
// on a tab close it is racing teardown. Marking it 'abandoned' late is still
// better than never, and duration_ms is recorded so a paper closed after two
// minutes is distinguishable from one closed after an hour.
async function abandonExam() {
  // reviewPaper() hides the results overlay, so examFinished becomes false
  // again. A fully saved attempt is still complete and must never be demoted.
  if (!examAttemptId || examFinished.value || attemptSaved.value) return;
  const id = examAttemptId;
  // cleared first so a route change racing beforeunload cannot send twice.
  examAttemptId = null;

  const elapsedMs = perfStart == null ? null : Math.round(performance.now() - perfStart);
  try {
    await abandonExamAttempt(supabase, id, elapsedMs);
  } catch (err) {
    // nothing useful to do - the page is going away regardless.
    console.error('abandonExam: could not close attempt', err);
  }
}

// fires on tab close / reload, where onBeforeUnmount does not run.
function handleBeforeUnload() {
  void abandonExam();
}

// the pdf.js viewer is a separate document, so it inherits none of the
// app's CSS custom properties. This copies the resolved values across under an
// --ss- prefix (prefixed to avoid colliding with pdf.js's own variables), and
// stamps data-page-mode so the injected stylesheet knows whether to invert the
// paper. Re-run whenever the theme changes.
const MIRRORED_TOKENS: Record<string, string> = {
  '--ss-accent': '--accent',
  '--ss-success': '--success',
  '--ss-danger': '--danger',
  '--ss-warning': '--warning',
  '--ss-muted': '--muted',
  '--ss-border': '--border',
  '--ss-text': '--text',
  '--ss-bg': '--background',
  '--ss-panel': '--secondary-background',
  '--ss-radius-pill': '--radius-pill',
  '--ss-font-mono': '--font-mono',
};

function syncIframeTheme(doc: Document) {
  const source = getComputedStyle(document.documentElement);
  const target = doc.documentElement;

  for (const [into, from] of Object.entries(MIRRORED_TOKENS)) {
    target.style.setProperty(into, source.getPropertyValue(from).trim());
  }

  // exam-paper is the only light theme; the other two want an inverted
  // page. Driven off the shared theme state rather than sniffing colours, so
  // adding a theme is one edit in theme.ts.
  target.dataset.pageMode = isLightTheme.value ? 'light' : 'dark';
}

function injectStyles(doc: Document) {
  syncIframeTheme(doc);

  const style = doc.createElement('style');
  style.type = 'text/css';
  style.id = 'smartsolver-overlay-styles';
  // fully restyled. The previous rules painted focus areas in
  // rgba(0,255,0,0.3) and timers in rgba(255,0,0,0.7) - saturated primaries
  // that read as debug output. Everything is now driven by the theme tokens
  // mirrored into this iframe by syncIframeTheme(), so the paper matches the
  // rest of the app in all three themes.
  style.textContent = `
      /* ---- dark paper -------------------------------------------------
         The PDF is a white raster. Inverting the CANVAS ONLY flips paper to
         near-black and ink to near-white; hue-rotate(180deg) puts coloured
         diagrams back to roughly their original hue rather than a negative.
         Scoped to the canvas deliberately: our overlays are siblings, so they
         are not inverted and keep their true theme colours. */
      /* Descendant selector, not '.page > canvas': pdf.js nests the canvas
         inside a .canvasWrapper, so the child combinator matched nothing and
         dark mode silently did nothing at all. Verified against the real DOM:
         .pdfViewer > .page > .canvasWrapper > canvas */
      [data-page-mode="dark"] .page canvas {
        filter: invert(1) hue-rotate(180deg);
      }
      /* The selection layer sits above the inverted canvas and must not be
         inverted with it, or highlighted text reads as a hole in the page. */
      [data-page-mode="dark"] .textLayer ::selection {
        background-color: color-mix(in srgb, var(--ss-accent) 45%, transparent);
      }
      [data-page-mode="dark"] .page {
        background-color: var(--ss-bg) !important;
      }

      /* ---- option highlights ----------------------------------------- */
      .highlight {
        position: absolute;
        cursor: pointer;
        z-index: 10;
        border-radius: 3px;
        background-color: transparent;
        transition: background-color 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
      }
      /* Neutral is invisible until pointed at - an untouched paper should look
         like a paper, not like a grid of yellow boxes. */
      .highlight.is-neutral:hover {
        background-color: color-mix(in srgb, var(--ss-accent) 20%, transparent);
      }
      .highlight.is-correct {
        background-color: color-mix(in srgb, var(--ss-success) 24%, transparent);
        box-shadow: inset 0 -2px 0 var(--ss-success);
      }
      .highlight.is-correct:hover {
        background-color: color-mix(in srgb, var(--ss-success) 34%, transparent);
      }
      .highlight.is-eliminated {
        background-color: color-mix(in srgb, var(--ss-danger) 14%, transparent);
        opacity: 0.6;
      }
      .highlight.is-eliminated:hover { opacity: 0.85; }
      /* Struck through rather than just tinted: "I ruled this out" is a
         different idea from "I chose this", and should not rely on colour
         alone to be legible. */
      .highlight.is-eliminated::after {
        content: '';
        position: absolute;
        left: 0; right: 0; top: 50%;
        height: 1.5px;
        transform: translateY(-50%);
        background-color: var(--ss-danger);
        opacity: 0.85;
      }

      /* ---- focus area -------------------------------------------------
         Was a full-width flat green block. Now a soft left-anchored wash with
         an accent rule, so it marks the question you are on without competing
         with the text you are reading. */
      .focus-area {
        width: 100%;
        position: absolute;
        pointer-events: none;
        z-index: 9;
        border-left: 3px solid color-mix(in srgb, var(--ss-accent) 45%, transparent);
        background: linear-gradient(
          90deg,
          color-mix(in srgb, var(--ss-accent) 14%, transparent) 0%,
          transparent 55%
        );
        transition: background 0.25s ease, border-color 0.25s ease;
      }
      /* The question currently under the reader's viewport. */
      .focus-area.is-active {
        border-left-color: var(--ss-accent);
        background: linear-gradient(
          90deg,
          color-mix(in srgb, var(--ss-accent) 24%, transparent) 0%,
          transparent 65%
        );
      }

      /* ---- per-question timer ---------------------------------------- */
      .focus-area-timer {
        position: absolute;
        top: 6px;
        right: 8px;
        padding: 3px 8px;
        border-radius: var(--ss-radius-pill);
        border: 1px solid var(--ss-border);
        background-color: var(--ss-panel);
        color: var(--ss-muted);
        font-family: var(--ss-font-mono);
        font-size: 10px;
        line-height: 1;
        letter-spacing: 0.04em;
        font-variant-numeric: tabular-nums;
        opacity: 0.5;
        transition: opacity 0.2s ease, color 0.2s ease, border-color 0.2s ease;
      }
      /* The timer for the question you are actually on. */
      .focus-area-timer.timer-active {
        opacity: 1;
        color: var(--ss-accent);
        border-color: color-mix(in srgb, var(--ss-accent) 55%, transparent);
      }

      html, :root, body { background: transparent !important; background-image: none !important; }
  `;

  (doc.head || doc.documentElement).appendChild(style);

  // PERFORMANCE BUG FIX - this pinned the main thread at 100% CPU.
  //
  // The observer below watches the `style` attribute across the whole iframe
  // subtree, and this handler wrote that same attribute back. setAttribute()
  // emits a mutation record EVEN WHEN THE VALUE IS UNCHANGED, so every styled
  // element re-triggered the observer, which rewrote it, forever. pdf.js puts
  // an inline style on every text-layer span - hundreds per page - so the
  // result was a perpetual microtask loop that never yielded: the tab burned a
  // full core and could not even paint (0 style recalcs while it ran).
  //
  // The fix is the `next !== current` guard. stripInlineBackground() is
  // idempotent (locked by tests/stripInlineBackground.test.ts), so the value
  // reaches a fixed point after one pass and the writes stop.
  const removeInlineBackground = (el: Element) => {
      if (!(el instanceof HTMLElement)) return;

      // BUG FIX - highlights rendered but were invisible.
      //
      // This observer exists to strip the white page backgrounds pdf.js paints
      // inline. But highlights and focus areas ARE inline background colours:
      // markNeutral()/markCorrect()/markEliminated() set style.backgroundColor,
      // and renderHighlights appends the div into the page, which the observer
      // sees as a childList mutation and immediately strips. Every highlight
      // was created correctly and then wiped a microtask later.
      //
      // Long-standing, not new: the same filter and the same markNeutral() call
      // are present in the original merge commit. It was previously masked by
      // the runaway-observer bug, which pinned the thread so hard that
      // rendering often never completed at all.
      if (OWNED_CLASSES.some(c => el.classList.contains(c))) return;

      const current = el.getAttribute('style');
      if (!current) return;

      const next = stripInlineBackground(current);
      if (next === null) {
        el.removeAttribute('style');
        return;
      }
      if (next !== current) el.setAttribute('style', next);
  };

  doc.querySelectorAll<HTMLElement>('*[style]').forEach(removeInlineBackground);

  observer = new MutationObserver(mutations => {
      for (const m of mutations) {
        if (m.type === 'attributes' && m.attributeName === 'style' && m.target instanceof Element) {
          removeInlineBackground(m.target as Element);
        }

        if (m.type === 'childList' && m.addedNodes.length) {
          m.addedNodes.forEach(node => {
            if (node instanceof Element) {
              if ((node as Element).hasAttribute('style')) removeInlineBackground(node as Element);
              (node as Element).querySelectorAll('*[style]').forEach(removeInlineBackground);
            }
          });
        }
      }
  });

  observer.observe(doc.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ['style'],
  });
}

// elements this app creates inside the pdf.js iframe. Their inline
// background IS the feature, so the background-stripping observer must leave
// them alone. Kept next to the observer rather than inline so adding a new
// decorated element is one edit in one place.
const OWNED_CLASSES = ['highlight', 'focus-area', 'focus-area-timer'] as const;

const pageLoadedState: Map<number, boolean> = new Map();

function observePageLoadState(
  pageIndex: number,
  pageEl: HTMLElement
) {
  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (
        m.type === "attributes" &&
        m.attributeName === "data-loaded"
      ) {
        const isLoaded = pageEl.hasAttribute("data-loaded");

        if (!isLoaded) {
          pageLoadedState.set(pageIndex, false);
        } else {
          renderHighlights(
            highlightMode,
            eventLogs,
            highlights,
            totalScale,
            [pageIndex],
            reviewOnly
          );

          renderFocusAreas(
            focusAreas,
            totalScale,
            [pageIndex]
          );
          pageLoadedState.set(pageIndex, true);
        }
      }
    }
  });

  observer.observe(pageEl, {
    attributes: true,
    attributeFilter: ["data-loaded"],
  });
}

const onLoad = async (pdfBytes: Uint8Array) => {
  if (!iframeRef.value) return;

  const iframeWindow = iframeRef.value.contentWindow;
  if (!iframeWindow) return;

  register(window)
  register(iframeWindow)

  const doc = iframeWindow.document;

  injectStyles(doc)

  // was two `as any` casts. asPdfViewerWindow names the two globals the
  // vendored pdf.js viewer publishes on its window.
  const viewerWindow = asPdfViewerWindow(iframeWindow);
  const app = viewerWindow.PDFViewerApplication;
  const pdfjsLib = viewerWindow.pdfjsLib;

  await app.initializedPromise;

  const { pdfViewer, eventBus } = app;

  let dataReady = false;

  eventBus.on("pagesinit", () => {
    if (!dataReady) return;

    const pages = pdfViewer._pages;
    if (!Array.isArray(pages)) return;

    // was `pageView: any`.
    pages.forEach((pageView: PdfPageView, index: number) => {
      const pageEl = pageView?.div;
      if (!pageEl) return;

      pageLoadedState.set(
        index,
        pageEl.hasAttribute("data-loaded")
      );

      observePageLoadState(index, pageEl);

      if (pageEl.hasAttribute("data-loaded")) {

        renderHighlights(
          highlightMode,
          eventLogs,
          highlights,
          totalScale,
          [index],
          reviewOnly
        );
        renderFocusAreas(
          focusAreas,
          totalScale,
          [index]
        );
      }
    });
  });

  eventBus.on("scalechanging", () => {
    const scale = parseFloat(
      getComputedStyle(iframeWindow.document.documentElement)
        .getPropertyValue("--scale-factor")
    );

    if (!Number.isFinite(scale)) return;

    totalScale.value = scale;

    const loadedPageIndexes = Array.from(pageLoadedState.entries())
      .filter(([_, isLoaded]) => isLoaded)
      .map(([pageIndex]) => pageIndex);
      
    renderHighlights(
      highlightMode,
      eventLogs,
      highlights,
      totalScale,
      loadedPageIndexes,
      reviewOnly
    );

    renderFocusAreas(
      focusAreas,
      totalScale,
      loadedPageIndexes
    );
  });

  eventBus.on("pagesloaded", async () => {
    const pdf = await pdfjsLib.getDocument(pdfBytes).promise;

    const text = await extractText(pdf);
    const question_numbers = identifyQuestionNumbers(text);
    const segmentedQuestions = segmentQuestions(text, question_numbers);
    const optionsText = await getOptions(pdf, text, segmentedQuestions);

    highlights = createHighlights(optionsText);
    // a contiguous answer key can still be a truncated prefix. Comparing it
    // with the independently parsed question paper prevents missing questions
    // from being silently scored as wrong with default marks.
    const parsedQuestionCount = highlights.reduce(
      (count, pageHighlights) => count + pageHighlights.length,
      0,
    );
    if (answers?.length !== parsedQuestionCount) {
      loadError.value =
        `This paper could not be marked safely: found ${parsedQuestionCount} questions but ${answers?.length ?? 0} answers.`;
      return;
    }
    // hand the parsed tree to the shared session so the Overview panel can
    // show real per-question state instead of placeholder rows.
    registerExamHighlights(highlights);

    // seed one Overview row per question, with that question's real option
    // count. The panel previously rendered `v-for="i in 40"` - a hardcoded 40
    // rows regardless of the paper, each showing invented answers.
    seedQuestions(
      highlights.flatMap((page, pageIndex) =>
        page.map((segment, segmentIndex) => ({
          questionNumber: computeGlobalIndex(highlights, pageIndex, segmentIndex),
          optionCount: segment.length,
        })),
      ),
    );
    focusAreas = createFocusAreas(segmentedQuestions);

    dataReady = true;

    eventBus.dispatch("pagesinit");

    eventListenersInit(focusAreas, totalScale, eventLogs);
    stopFocusTimer?.();
    stopFocusTimer = startFocusAreaTimer(0, focusAreas);

    examLoaded.value = true;
  });
};


async function setup() {
  const iframe = iframeRef.value;
  if (!iframe) return;
  iframe.style.background = 'transparent';
  iframe.setAttribute('allowtransparency', 'true');

  try {
    const {
      answers: answersFromPDF,
      pdfBytes,
      pdfUrl,
      answerKeyPersisted,
      answerKeyError,
    } = await getPDF();
    answers = answersFromPDF;
    practiceWarning.value = answerKeyPersisted
      ? null
      : answerKeyError ?? 'Trusted marking is unavailable; this practice result will not be saved.';

    // an in-flight fetch can finish after route teardown; release its URL
    // immediately instead of storing it on an already-unmounted component.
    if (!iframeRef.value) {
      URL.revokeObjectURL(pdfUrl);
      return;
    }
    // retain the blob URL so route teardown can release its backing bytes.
    if (pdfObjectUrl) URL.revokeObjectURL(pdfObjectUrl);
    pdfObjectUrl = pdfUrl;
    // listen before navigation so a fast cached viewer cannot win the race.
    iframeLoadHandler = () => {
      iframeLoadHandler = null;
      void onLoad(pdfBytes);
    };
    iframe.addEventListener('load', iframeLoadHandler, { once: true });
    iframeRef.value.src = '/web/viewer.html?file=' + encodeURIComponent(pdfUrl);
  } catch (err) {
    // fetch-pdf returns 404 when the question paper or the mark scheme is
    // not on the upstream mirror - a real outcome for an uncommon
    // series/variant, not a bug. Surfaced so the student can go back and pick
    // another rather than waiting on a load that will never finish.
    console.error('paper load failed:', err);
    loadError.value =
      'This paper could not be loaded. It may not exist for that series or variant.';
  }
}

onBeforeUnmount(() => {
  // close an attempt the student navigated away from. Deliberately FIRST -
  // the original body starts with `if (!iframeRef.value) return`, so anything
  // placed after that guard is skipped whenever the iframe is already gone,
  // which is exactly the teardown case this needs to cover.
  window.removeEventListener('beforeunload', handleBeforeUnload);
  void abandonExam();

  stopFocusTimer?.();
  stopFocusTimer = null;
  if (pdfObjectUrl) {
    URL.revokeObjectURL(pdfObjectUrl);
    pdfObjectUrl = null;
  }

  if(!iframeRef.value) return;
  if (iframeLoadHandler) {
    iframeRef.value.removeEventListener('load', iframeLoadHandler);
    iframeLoadHandler = null;
  }
  if (observer) {
    observer.disconnect();
    observer = null;
  }

  const iframeWindow = iframeRef.value.contentWindow;

  unregister(window);
  if (iframeWindow) unregister(iframeWindow);
});

// re-mirror the palette when the user switches theme mid-exam. Without
// this the paper would keep the old theme's colours (and stay inverted or not)
// until the page reloaded. Also puts the previously-unused `watch` import to
// work - it was one of the standing TS6133 warnings.
watch(currentTheme, () => {
  const doc = iframeRef.value?.contentDocument;
  if (doc) syncIframeTheme(doc);
});

onMounted(async () => {
  // clear any state left by a previously opened paper - this module-level
  // store outlives the component, so without it question 4's flags would carry
  // into the next paper.
  resetExamState();

  if (!session) {
    router.push("/login");
    return;
  }

  // catches tab close / reload, which onBeforeUnmount never sees.
  window.addEventListener('beforeunload', handleBeforeUnload);

  setup();
});

</script>

<template>

  <!-- @start is what actually begins the attempt - see LoadingScreen. -->
  <LoadingScreen
    :state="examLoaded"
    :schema="props.schema"
    :load-error="loadError"
    :practice-warning="practiceWarning"
    @start="startExam"
    @back="router.push('/browser')"
  ></LoadingScreen>

  <!-- results overlay. Fades in over the paper when the attempt ends. -->
  <Transition name="screen-fade">
    <EndScreen
      v-if="examFinished"
      :summary="summary"
      :saving="saving"
      :save-error="saveError"
      :can-retry="!!completionId && !!lastCompletion && !attemptSaved"
      @dashboard="goToDashboard"
      @review="reviewPaper"
      @retry="retrySave"
    />
  </Transition>

  <main class="solver-container" :class="{ 'solver-container--zen': zenMode }">
    <!-- review keeps navigation available but disables mutating tools. -->
    <ToolsContainer
      v-if="!zenMode"
      :read-only="reviewOnly"
      @end-exam="endExam"
    ></ToolsContainer>
    <header class="top-bar">
      <!-- the timer starts with the exam and freezes when review begins. -->
      <TopBar v-model:zen-mode="zenMode" :running="examStarted && !reviewOnly"/>
    </header>

    <section class="main-area">

      <div class="pdf-wrapper">
        <!-- the selected paper is assigned only after fetch-pdf succeeds. -->
        <iframe ref="iframeRef"
            id="pdf-viewer" 
            width="100%" 
            height="100%"
            src="about:blank"
            >
        </iframe>      
      </div>

      <aside
        v-if="!zenMode"
        class="overview-drawer"
        :class="{ 'overview-drawer--open': showOverview }"
      >
        <SideWindow/>
      </aside>
    </section>

    <!-- BottomBar had no End Exam control, so endExam() was unreachable. -->
    <BottomBar
      v-if="!zenMode"
      :schema="props.schema"
      :read-only="reviewOnly"
      :saved="attemptSaved"
      @end-exam="endExam"
    ></BottomBar>
  </main>
</template>
<style lang="scss" scoped>
.solver-container {
  position: relative;
  background-color: $background;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.top-bar {
  width: 100%;
  flex: 0 0 auto;
  height: 56px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.main-area {
  position: relative;
  flex: 1 1 auto;
  overflow: hidden;
}

.pdf-wrapper {
  position: absolute;
  inset: 0;
}
.pdf-wrapper iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.overview-drawer {
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 320px;
  transform: translateX(320px);
  transition: transform 0.2s ease-out;
}

.overview-drawer--open {
  transform: translateX(0);
}
</style>
