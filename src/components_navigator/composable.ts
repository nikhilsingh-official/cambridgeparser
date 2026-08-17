import { ref } from "vue";
// imports added for the exam-session accessors below.
import type { EventLogs } from "@/lib/utils/utilsTypes";
import { getActiveFocusArea, type DocumentFocusAreas } from "@/lib/focusAreas";

const showOverview = ref(false);
const showTools = ref(false);

export function getShowStates() {
    return { showOverview, showTools }
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

/** Called once by MCQNav after the focus areas exist. */
export function registerExamSession(eventLogs: EventLogs, focusAreas: DocumentFocusAreas) {
    examEventLogs = eventLogs;
    examFocusAreas = focusAreas;
}

export function getExamSession() {
    return {
        eventLogs: () => examEventLogs,
        activeQuestionNumber: () => getActiveFocusArea(examFocusAreas)?.questionNumber ?? 0,
    };
}
