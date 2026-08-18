import type { Ref } from "vue";
import type { DocumentHighlights, OptionHighlights, OptionState, SegmentHighlights, Highlight } from "./highlightTypes";
import { computeGlobalIndex } from "../utils/computeGlobalIndex";
import type { EventLogs } from "@/lib/utils/utilsTypes";
// switched to the typed highlight constructor; HighlightAction and
// HighlightMode come from the central enum module.
import { logHighlight } from "../utils/addEventLog";
import { HighlightAction, type HighlightMode } from "@/lib/types/enums";
// keeps the Overview panel in step with the paper.
import { setOptionState } from "@/lib/state/examState";

// highlights used to be painted with inline `style.backgroundColor` set to
// raw rgba(0,255,0) / rgba(255,0,0) / rgba(255,255,0) - saturated primaries that
// looked like debug output and ignored the theme entirely.
//
// They are now CSS classes, styled in the stylesheet MCQNav injects into the
// pdf.js iframe. Three things fall out of that:
//   - they follow the active theme, because the injected CSS uses the theme
//     tokens that are mirrored into the iframe;
//   - they can have hover/transition/border treatment, which inline colours
//     could not express;
//   - they no longer set an inline background at all, so the observer that
//     strips inline backgrounds from pdf.js elements can never wipe them. That
//     was the cause of "no highlights are rendered anymore".
const STATE_CLASS: Record<OptionState, string> = {
  correct: "is-correct",
  eliminated: "is-eliminated",
  neutral: "is-neutral",
};

const ALL_STATE_CLASSES = Object.values(STATE_CLASS);

function applyState(elements: HTMLElement | HTMLElement[], state: OptionState) {
  const list = Array.isArray(elements) ? elements : [elements];
  for (const el of list) {
    el.classList.remove(...ALL_STATE_CLASSES);
    el.classList.add(STATE_CLASS[state]);
  }
}

/** kept as a named export - renderHighlights uses it to seed new elements. */
export function markNeutral(elements: HTMLElement[] | HTMLElement) {
  applyState(elements, "neutral");
}

function updateOptionState(optionHighlights: Highlight[], domElements: HTMLElement[], state: OptionState) {
  optionHighlights.forEach(h => h.state = state);
  applyState(domElements, state);
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
        // choosing a new option clears the old one in the DOM; mirror that
        // in the store too, or the Overview would show two selected options.
        setOptionState(
          computeGlobalIndex(highlights, pageIndex, segmentIndex),
          currentCorrectIndex,
          "neutral",
        );
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

  // mirror the change into the reactive overview store. Done here rather
  // than in updateOptionState so it fires once per user action, with the
  // question number already resolved.
  setOptionState(questionNumber, optionIndex, nextState);
}