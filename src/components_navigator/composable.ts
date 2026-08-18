import { computed, ref, type Ref } from "vue";
// imports added for the exam-session accessors below.
import type { EventLogs, HighlightMode } from "@/lib/utils/utilsTypes";
import { getActiveFocusArea, type DocumentFocusAreas } from "@/lib/focusAreas";
import type { DocumentHighlights } from "@/lib/highlights";

const showOverview = ref(false);
const showTools = ref(false);

export function getShowStates() {
    return { showOverview, showTools }
}

// BUG FIX - the Tools panel and the C/E keybinds were two separate states.
//
// MCQNav owned `highlightMode` and handed it to createKeydownHandlers, so
// pressing C or E updated the paper. HighlightModeSlider meanwhile declared its
// own `defineModel({ type: Boolean })` and was mounted with NO v-model at all,
// so its toggle drove a local boolean that nothing read. The two could never
// agree: keys moved the paper without moving the switch, and the switch moved
// nothing at all.
//
// The mode now lives here, module-level, exactly like showOverview/showTools -
// one source of truth that the keybinds, the slider, the bottom-bar indicator
// and the paper renderer all share.
export const highlightMode: Ref<HighlightMode> = ref("correct");

export function getHighlightMode() {
    return {
        highlightMode,
        isCorrectMode: computed(() => highlightMode.value === "correct"),
        setMode: (mode: HighlightMode) => { highlightMode.value = mode; },
        toggleMode: () => {
            highlightMode.value = highlightMode.value === "correct" ? "eliminated" : "correct";
        },
    };
}

// everything below is new.
//
// ActiveQuestionButtons sits three levels below MCQNav (MCQNav ->
// ToolsContainer -> ActiveQuestionButtons) and needs two things to log a flag:
// the exam's event log, and which question is currently focused. Threading both
// through ToolsContainer as props would change a component that has no other
// reason to know about them, so they are registered here instead - the same
// module-level shared-state pattern getShowStates() already uses.
//
// focusAreas is created with reactive(), so reading the active area at click
// time always reflects the question the student is actually looking at.
let examEventLogs: EventLogs = [];
let examFocusAreas: DocumentFocusAreas = [];
// the overview needs the highlight tree to know what has been selected or
// eliminated per question, so it is registered alongside the other two.
const examHighlights: Ref<DocumentHighlights> = ref([]);

/** Called once by MCQNav after the focus areas exist. */
export function registerExamSession(
    eventLogs: EventLogs,
    focusAreas: DocumentFocusAreas,
    highlights?: DocumentHighlights,
) {
    examEventLogs = eventLogs;
    examFocusAreas = focusAreas;
    if (highlights) examHighlights.value = highlights;
}

/** called again once the PDF has been parsed and highlights exist. */
export function registerExamHighlights(highlights: DocumentHighlights) {
    examHighlights.value = highlights;
}

export function getExamHighlights() {
    return examHighlights;
}

export function getExamSession() {
    return {
        eventLogs: () => examEventLogs,
        activeQuestionNumber: () => getActiveFocusArea(examFocusAreas)?.questionNumber ?? 0,
    };
}
