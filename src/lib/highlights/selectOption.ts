import type { Ref } from "vue";
import type { DocumentHighlights, OptionHighlights, OptionState, SegmentHighlights, Highlight } from "./highlightTypes";
import { computeGlobalIndex } from "../utils/computeGlobalIndex";
import type { EventLogs } from "@/lib/utils/utilsTypes";
import { addEventLog } from "../utils/addEventLog";

function setHighlightColor(
  elements: HTMLElement | HTMLElement[],
  r: number,
  g: number,
  b: number,
  alpha = 0.3
) {
  const color = `rgba(${r}, ${g}, ${b}, ${alpha})`;

  if (Array.isArray(elements)) {
    elements.forEach(el => el.style.backgroundColor = color);
  } else {
    elements.style.backgroundColor = color;
  }
}

function markCorrect(elements: HTMLElement[] | HTMLElement) {
  setHighlightColor(elements, 0, 255, 0);
}

function markEliminated(elements: HTMLElement[] | HTMLElement) {
  setHighlightColor(elements, 255, 0, 0);
}

export function markNeutral(elements: HTMLElement[] | HTMLElement) {
  setHighlightColor(elements, 255, 255, 0);
}

function updateOptionState(optionHighlights: Highlight[], domElements: HTMLElement[], state: OptionState) {
  optionHighlights.forEach(h => h.state = state);
  if (state === "correct") markCorrect(domElements);
  else if (state === "eliminated") markEliminated(domElements);
  else markNeutral(domElements);
}

const logMap: Record<string, string> = {
  "correct_correct": "deselectedCorrect",
  "correct_eliminated": "elimToCorrect",
  "correct_neutral": "setCorrect",
  "eliminated_correct": "correctToElim",
  "eliminated_eliminated": "deselectedElim",
  "eliminated_neutral": "setElim",
};

export function selectOption(highlightMode: Ref<"correct" | "eliminated">, eventLogs: EventLogs, pageIndex: number, segmentIndex: number, optionIndex: number, highlights: DocumentHighlights, groupHighlights: HTMLElement[]) {

  const currentSegHighlights: SegmentHighlights | undefined = highlights[pageIndex]?.[segmentIndex]
  const currentOptionHighlights: OptionHighlights | undefined = highlights[pageIndex]?.[segmentIndex]?.[optionIndex]
  if(!currentSegHighlights) return
  if(!currentOptionHighlights) return

  console.log("Highlight Group Array: ")
  console.log(groupHighlights)

  const optionState = currentOptionHighlights[0]?.state;
  if(!optionState) return;

  if (highlightMode.value === "correct") {
    const currentCorrect = currentSegHighlights.filter(x => x[0]?.state === "correct")[0];
    if (currentCorrect) {
      const currentCorrectIndex = currentSegHighlights.indexOf(currentCorrect);
      const elements = currentCorrect.map(h => h.el).filter(Boolean) as HTMLElement[];
      if (elements.length) {
        markNeutral(elements);
        highlights[pageIndex]![segmentIndex]![currentCorrectIndex]?.forEach(h => h.state = "neutral");
      }
    }
  }

  let nextState: OptionState;

  if (optionState === highlightMode.value) {
    nextState = "neutral";
  } else {
    nextState = highlightMode.value;
  }

  const questionNumber = computeGlobalIndex(highlights, pageIndex, segmentIndex);

  updateOptionState(currentOptionHighlights, groupHighlights, nextState);

  const key = `${nextState}_${optionState}`;
  const logString = logMap[key];
  if (logString) addEventLog(eventLogs, "highlight", logString, questionNumber, optionIndex);
}