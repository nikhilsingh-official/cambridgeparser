import type { ButtonType } from "../buttons";

export type FocusAreaActions = "userHoveredIn" | "userHoveredOutPage" | "userClick";
export type HighlightActions = "deselectedCorrect" | "elimToCorrect" | "setCorrect" | "correctToElim" | "deselectedElim" | "setElim";
export type ButtonActions = "Selection" | "Deselection";

// added `seq` and `elapsedMs` so the event stream can be persisted to
// attempt_events. Everything else is unchanged.
export type EventLogs = Array<{ dateTimestamp: string, performanceTimestamp: number, timezone: string, elementType: ButtonType | "focusArea" | "highlight", actionType: ButtonActions | FocusAreaActions | HighlightActions, question: number, option?: number, seq?: number, elapsedMs?: number }>;
export type HighlightMode = "correct" | "eliminated"
