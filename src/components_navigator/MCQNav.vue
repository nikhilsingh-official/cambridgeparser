<script setup lang="ts">
import LoadingScreen from './LoadingScreen.vue';
// the results screen shown when the attempt ends.
import EndScreen from './EndScreen.vue';
import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue';
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
import type { HighlightMode, EventLogs } from '@/lib/utils/utilsTypes';
import { enrichAnalytics } from '@/lib/processing/enrichAnalytics';
import { getQuestionsAnalytics } from '@/lib/processing/getQuestionAnalytics';
// pushQuestionMetrics added - the weighted scores now live in their own
// versioned table rather than inline on question_attempts.
import { pushToAttemptsTable, pushQuestionMetrics } from '@/lib/supabase/pushToAttemptsTable';
// the one-shot pushToExamTable is replaced by the two-phase lifecycle.
import { startExamAttempt, finishExamAttempt } from '@/lib/supabase/pushToExamTable';
// new writers for the raw event stream and the cached mark-scheme key.
import { pushEventLogs } from '@/lib/supabase/pushEventLogs';
import { cacheAnswerKey } from '@/lib/supabase/cacheAnswerKey';
// exam-relative event timing, and the shared session the flag buttons read.
import { setEventEpoch } from '@/lib/utils/addEventLog';
import { registerExamSession } from './composable';
import router from '@/router/router';
// types for the vendored pdf.js viewer and the fetch-pdf contract.
import { asPdfViewerWindow, type PdfPageView } from '@/lib/types/pdfViewer';
import type { FetchPdfResponse, LoadedPaper } from '@/lib/types/fetchPdf';
// local summary computation for the end screen.
import { buildExamSummary, type ExamSummary } from '@/lib/types/examSummary';
import { renderHighlights } from '@/lib/render/renderHighlights';
import { renderFocusAreas } from '@/lib/render/renderFocusAreas';

const { showOverview } = getShowStates();
  
let perfStart: number | null;
const examLoaded = ref(false);
const examStarted = ref(false);

const iframeRef = ref<HTMLIFrameElement | null>(null);
let observer: MutationObserver | null = null;

const props = defineProps<{
  schema: string
}>();

const highlightMode: Ref<HighlightMode> = ref("correct");
let eventLogs: EventLogs = [];
let highlights: DocumentHighlights = [];
let focusAreas: DocumentFocusAreas = [];
const totalScale = ref(1);

const { register, unregister } = createKeydownHandlers(highlightMode);
const { session } = useAuthStore();

// `dateStart` removed - it existed only to back-date started_at in the old
// one-shot write. startExamAttempt() now stamps started_at when the attempt
// actually opens, so nothing consumed it any more.
let answers: TableRow[] | null = null;
// held for the duration of the attempt - opened in startExam(), written to
// throughout, closed in endExam().
let examAttemptId: string | null = null;

// end-screen state. `examFinished` drives the overlay; `summary` is null
// until endExam() has marked the paper, which is what shows the interim
// "Marking your paper..." state.
const examFinished = ref(false);
const summary = ref<ExamSummary | null>(null);
const saving = ref(false);
const saveError = ref<string | null>(null);

// the fetch-pdf edge function's response had no type at all - `answers`
// was `any`, so the mark-scheme rows flowed untyped into getQuestionsAnalytics
// and cacheAnswerKey. FetchPdfResponse/LoadedPaper name that contract.
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
  const answers = body.answers;

  const pdfBytes = new Uint8Array(
    Array.isArray(body.qp)
      ? body.qp
      : Object.values(body.qp)
  );

  const pdfBlob = new Blob([pdfBytes], {
    type: "application/pdf"
  });

  const pdfUrl = URL.createObjectURL(pdfBlob);

  return { answers, pdfBytes, pdfUrl };
}


// the attempt row is now opened here rather than at endExam(), so an
// abandoned paper is still recorded and started_at is an observation instead of
// a value the client back-dates at the end.
async function startExam() {
  perfStart = performance.now();
  // anchor event timing to exam start so stored elapsed_ms is meaningful.
  setEventEpoch(perfStart);
  // hand the event log and focus areas to the shared exam session so the
  // flag buttons in ToolsContainer can log against the focused question.
  registerExamSession(eventLogs, focusAreas);
  examStarted.value = true;

  try {
    // `session` is Session | null - typing startExamAttempt surfaced that it
    // was being passed unchecked. It is also captured once at setup (Pinia
    // destructuring is not reactive), so a session that arrives later leaves
    // this null; see FUTURE_WORK.md.
    if (!session) throw new Error('No Supabase session; attempt not persisted');
    examAttemptId = await startExamAttempt(supabase, props, session, answers?.length);
    // cache the mark-scheme key so the DB can decide correctness itself.
    if (answers) await cacheAnswerKey(supabase, props.schema, answers);
  } catch (err) {
    // a failed open must not block the student from sitting the paper. The
    // attempt simply is not persisted; endExam() detects the null id.
    console.error('startExam: could not open attempt', err);
  }
}

async function endExam() {
  // the results screen goes up immediately, before any network work, so
  // the candidate is never left looking at the paper wondering if it worked.
  examFinished.value = true;
  saving.value = true;
  saveError.value = null;

  try {
    if(!answers) return;
    const questionsData = getQuestionsAnalytics(highlights, focusAreas, answers);
    const enrichedData = enrichAnalytics(questionsData, eventLogs);

    if (perfStart == null) throw new Error("Exam hasn't started");

    const elapsedMs = Math.round(performance.now() - perfStart);

    // marked locally from data already in hand, so the score paints even if
    // every write below fails. The database remains authoritative.
    summary.value = buildExamSummary(props.schema, questionsData, answers, elapsedMs);

    // fall back to opening one now if startExam() could not.
    if (!examAttemptId) {
      // same null guard as in startExam().
      if (!session) throw new Error('No Supabase session; attempt not persisted');
      examAttemptId = await startExamAttempt(supabase, props, session, answers.length);
    }

    const answeredCount = questionsData.filter(q => q.selectedOption != null).length;

    const insertedQuestions = await pushToAttemptsTable(supabase, examAttemptId, enrichedData);
    // weighted scores go to the versioned question_metrics table.
    await pushQuestionMetrics(supabase, insertedQuestions ?? [], enrichedData);
    // persist the raw stream - previously discarded at this exact point.
    await pushEventLogs(supabase, examAttemptId, eventLogs);
    await finishExamAttempt(supabase, examAttemptId, elapsedMs, answeredCount, 'completed');

    return { examAttemptId, insertedCount: Array.isArray(insertedQuestions) ? insertedQuestions.length : 0 };
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

function injectStyles(doc: Document) {
  const style = doc.createElement('style');
  style.type = 'text/css';
  style.textContent = `
      .highlight { 
        position: absolute; 
        cursor: pointer; 
        z-index: 10; 
      }
      .focus-area {
        width: 100%;
        background-color: rgba(0, 255, 0, 0.3) !important;
        position: absolute;
        pointer-events: none;
        z-index: 9;
      }
      .focus-area-timer { position: absolute; top: 0; right: 0; background-color: rgba(255, 0, 0, 0.7); }
      html, :root, body { background: transparent !important; background-image: none !important; }
  `;

  (doc.head || doc.documentElement).appendChild(style);

  const removeInlineBackground = (el: Element) => {
      if (!(el instanceof HTMLElement)) return;
      const s = el.getAttribute('style');
      if (!s) return;
      const parts = s
        .split(';')
        .map(p => p.trim())
        .filter(p => p.length && !/^\s*(background|background-image|background-color)\s*:/i.test(p));
      if (parts.length) el.setAttribute('style', parts.join('; '));
      else el.removeAttribute('style');
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
          console.log(
            "Page became unloaded:",
            pageIndex
          );
          pageLoadedState.set(pageIndex, false);
        } else {
          console.log(
            "Page became loaded:",
            pageIndex
          );

          renderHighlights(
            highlightMode,
            eventLogs,
            highlights,
            totalScale,
            [pageIndex]
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
          [index]
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
    console.log(`New Scale: ${scale}`);

    const loadedPageIndexes = Array.from(pageLoadedState.entries())
      .filter(([_, isLoaded]) => isLoaded)
      .map(([pageIndex]) => pageIndex);
      
    renderHighlights(
      highlightMode,
      eventLogs,
      highlights,
      totalScale,
      loadedPageIndexes
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
    focusAreas = createFocusAreas(segmentedQuestions);

    dataReady = true;

    eventBus.dispatch("pagesinit");

    eventListenersInit(focusAreas, totalScale, eventLogs);
    startFocusAreaTimer(0, focusAreas);

    examLoaded.value = true;
  });
};


async function setup() {
  const iframe = iframeRef.value;
  if (!iframe) return;
  iframe.style.background = 'transparent';
  iframe.setAttribute('allowtransparency', 'true');

  const { answers: answersFromPDF, pdfBytes, pdfUrl } = await getPDF();
  answers = answersFromPDF;

  if (!iframeRef.value) return;
  iframeRef.value.src = '/web/viewer.html?file=' + encodeURIComponent(pdfUrl);

  iframe.addEventListener('load', () => onLoad(pdfBytes));
}

onBeforeUnmount(() => {
  if(!iframeRef.value) return;
  iframeRef.value.removeEventListener('load', () => onLoad);
  if (observer) {
    observer.disconnect();
    observer = null;
  }

  const iframeWindow = iframeRef.value.contentWindow;

  unregister(window);
  if (iframeWindow) unregister(iframeWindow);
});

onMounted(async () => {
  if (!session) {
    router.push("/login");
    return;
  }

  setup();
});

</script>

<template>

  <!-- @start is what actually begins the attempt - see LoadingScreen. -->
  <LoadingScreen
    :state="examLoaded"
    :schema="props.schema"
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
      @dashboard="goToDashboard"
      @review="reviewPaper"
    />
  </Transition>

  <main class="solver-container">
    <ToolsContainer></ToolsContainer>
    <header class="top-bar">
      <TopBar/>
    </header>

    <section class="main-area">

      <div class="pdf-wrapper">
        <iframe ref="iframeRef"
            id="pdf-viewer" 
            width="100%" 
            height="100%"
            src="/web/viewer.html?file=/9608_w21_qp_11.pdf"
            >
        </iframe>      
      </div>

      <aside
        class="overview-drawer"
        :class="{ 'overview-drawer--open': showOverview }"
      >
        <SideWindow/>
      </aside>
    </section>

    <!-- BottomBar had no End Exam control, so endExam() was unreachable. -->
    <BottomBar @end-exam="endExam"></BottomBar>
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