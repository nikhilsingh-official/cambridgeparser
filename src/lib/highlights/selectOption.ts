import type { Ref } from "vue";
import type { DocumentHighlights, OptionHighlights, OptionState, SegmentHighlights, Highlight } from "./highlightTypes";
import { computeGlobalIndex } from "../utils/computeGlobalIndex";
import type { EventLogs } from "@/lib/utils/utilsTypes";
// switched to the typed highlight constructor; HighlightAction and
// HighlightMode come from the central enum module.
import { logHighlight } from "../utils/addEventLog";
import { HighlightAction, type HighlightMode } from "@/lib/types/enums";

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

// was `Record<string, string>`, which meant the compiler knew nothing about
// either the keys or the values - a typo in a key silently produced `undefined`
// and no event, and the values were plain strings that had to be cast on the way
// into the event log.
//
// The key is now a template-literal type, so the map is exhaustive by
// construction: it must contain exactly one entry for every
// (mode, previous state) pair, and `logMap[key]` is known to be a
// HighlightAction rather than a string. Adding a fourth OptionState or a third
// HighlightMode becomes a compile error here instead of a silent no-op.
type TransitionKey = `${HighlightMode}_${OptionState}`;

const logMap: Record<TransitionKey, HighlightAction> = {
  "correct_correct": HighlightAction.DeselectedCorrect,
  "correct_eliminated": HighlightAction.ElimToCorrect,
  "correct_neutral": HighlightAction.SetCorrect,
  "eliminated_correct": HighlightAction.CorrectToElim,
  "eliminated_eliminated": HighlightAction.DeselectedElim,
  "eliminated_neutral": HighlightAction.SetElim,
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

  // BUG FIX, surfaced by typing this lookup.
  //
  // This read `${nextState}_${optionState}`, but logMap is keyed by
  // (mode, previous state) - the smartsolver original was
  // `${highlightMode.value}_${optionState}`. Because nextState is "neutral"
  // whenever the student deselects, the key became "neutral_correct" or
  // "neutral_eliminated", neither of which is in the map. The old
  // `if (logString)` guard then silently swallowed it, so DESELECTION EVENTS
  // WERE NEVER LOGGED: "deselectedCorrect" and "deselectedElim" could not occur,
  // and enrichAnalytics' elimination-reversal count was correspondingly wrong.
  //
  // Typing the key as TransitionKey makes the lookup total - all six
  // (mode x previous state) combinations exist, so no guard is needed and a
  // missing entry is a compile error rather than a dropped event.
  const key: TransitionKey = `${highlightMode.value}_${optionState}`;
  logHighlight(eventLogs, logMap[key], questionNumber, optionIndex);
}