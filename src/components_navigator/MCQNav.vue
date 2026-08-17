<script setup lang="ts">
import LoadingScreen from './LoadingScreen.vue';
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
import { pushToAttemptsTable } from '@/lib/supabase/pushToAttemptsTable';
import { pushToExamTable } from '@/lib/supabase/pushToExamTable';
import router from '@/router/router';
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

let dateStart = "";
let answers: TableRow[] | null = null;

async function getPDF(): Promise<{ answers: any; pdfBytes: Uint8Array; pdfUrl: string }> {

  const { data, error } = await supabase.functions.invoke("fetch-pdf", {
    body: {
      schema: props.schema
    }
  });

  if (error) {
    console.error("fetch-pdf error:", error);
    throw error;
  }

  const answers = data.answers;

  const pdfBytes = new Uint8Array(
    Array.isArray(data.qp)
      ? data.qp
      : Object.values(data.qp)
  );

  const pdfBlob = new Blob([pdfBytes], {
    type: "application/pdf"
  });

  const pdfUrl = URL.createObjectURL(pdfBlob);

  return { answers, pdfBytes, pdfUrl };
}


function startExam() {
  perfStart = performance.now();
  dateStart = new Date().toISOString()
  examStarted.value = true;
}

async function endExam() {
  try {
    if(!answers) return;
    const questionsData = getQuestionsAnalytics(highlights, focusAreas, answers);
    const enrichedData = enrichAnalytics(questionsData, eventLogs);

    if (perfStart == null) throw new Error("Exam hasn't started");

    const elapsedMs = Math.round(performance.now() - perfStart);
    const finishedAtIso = new Date().toISOString();

    const examAttemptId = await pushToExamTable(supabase, props, session, elapsedMs, dateStart, finishedAtIso);

    const insertedQuestions = await pushToAttemptsTable(supabase, examAttemptId, enrichedData);

    return { examAttemptId, insertedCount: Array.isArray(insertedQuestions) ? insertedQuestions.length : 0 };
  } catch (err) {
    console.error('endExam failed', err);
    throw err;
  }
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

  const app = (iframeWindow as any).PDFViewerApplication;
  const pdfjsLib = (iframeWindow as any).pdfjsLib;

  await app.initializedPromise;

  const { pdfViewer, eventBus } = app;

  let dataReady = false;

  eventBus.on("pagesinit", () => {
    if (!dataReady) return;

    const pages = pdfViewer._pages;
    if (!Array.isArray(pages)) return;

    pages.forEach((pageView: any, index: number) => {
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

  <LoadingScreen :state="examLoaded"></LoadingScreen>

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

    <BottomBar></BottomBar>
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